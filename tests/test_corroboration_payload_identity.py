"""Two independent sources may report the SAME value — the corroboration path.

Red-first. `payloads` is keyed `payload_hash TEXT PRIMARY KEY`, and
`payload_hash = SHA256(canonical_json({belief_id, value, verifiability}))`. Two
independent sources reporting the same value for the same belief therefore produce
BYTE-IDENTICAL payloads, hence the same payload_hash — and the second insert violates
the primary key.

That is not an exotic edge case. It is the corroboration path, and V0 §2 makes it the
whole basis of promotion:

    "Minimum sample floor (corroboration gate, §2/§4). v0: **2** independent
     corroborating sources required for `unverified -> verified` via corroboration."

A schema that cannot store the second corroborating source cannot corroborate anything.
The gate is unreachable by construction.

The contradiction is structural, not incidental: the `payloads` table carries `event_id`
(one row per EVENT, 1:1) while being keyed by CONTENT (one row per distinct payload,
n:1). Both cannot hold. See decisions/0007.
"""

from __future__ import annotations

import pytest

from nyx import projection, storage
from nyx.skeleton import record_observation

BELIEF_ID = "entity:legion/property:ram"

# The SAME claim — identical {belief_id, value, verifiability}, so identical canonical
# payload and identical payload_hash — reported by two INDEPENDENT sources at different
# times. This is exactly what corroboration means.
FIRST_SOURCE = {
    "belief_id": BELIEF_ID,
    "value": "64GB",
    "verifiability": "externally_checkable",
    "occurred_at": "2026-07-12T00:00:00+00:00",
    "source": {"actor_id": "sensor:hwscan", "config": {}},
    "source_class": "direct_observation",
}
SECOND_SOURCE = {
    "belief_id": BELIEF_ID,
    "value": "64GB",  # SAME value — that is the point
    "verifiability": "externally_checkable",
    "occurred_at": "2026-07-12T06:00:00+00:00",  # different time
    "source": {"actor_id": "invoice:oem-manifest", "config": {}},  # different source
    "source_class": "vendor_document",  # different source CLASS (§2 counts distinct classes)
}


@pytest.fixture()
def db_path(tmp_path):
    path = str(tmp_path / "nyx.db")
    storage.init_db(path, create=True).close()
    return path


def test_two_sources_reporting_the_same_value_both_persist(db_path):
    """Both corroborating events must land in Layer A. Today the second one collides."""
    record_observation(db_path, FIRST_SOURCE)
    record_observation(db_path, SECOND_SOURCE)

    conn = storage.init_db(db_path)
    try:
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        payloads = conn.execute("SELECT COUNT(*) FROM payloads").fetchone()[0]
    finally:
        conn.close()

    assert events == 2  # two distinct events: different source, different occurred_at
    assert payloads == 2  # ...and each event owns its own payload row


def test_corroborating_event_reaches_the_support_set(db_path):
    """The second source must be visible as support — otherwise the §2 corroboration
    gate (2 independent sources to promote) can never be evaluated, let alone met."""
    record_observation(db_path, FIRST_SOURCE)
    belief = record_observation(db_path, SECOND_SOURCE)
    assert len(belief["supporting_events"]) == 2
    assert belief["current_value"] == "64GB"


def test_identical_payloads_do_not_share_one_payload_row(db_path):
    """Each event owns its payload row — content-identical payloads must NOT be pooled.

    Beyond corroboration, this is an Invariant 14 (erasure boundary) requirement. Payloads
    are separately destroyable by crypto-shredding, per EVENT. If two events shared a
    single payload row keyed by content, redacting one event would destroy the other
    event's payload too — silent collateral erasure of a record nobody asked to erase.
    """
    record_observation(db_path, FIRST_SOURCE)
    record_observation(db_path, SECOND_SOURCE)

    conn = storage.init_db(db_path)
    try:
        rows = conn.execute("SELECT event_id, payload_hash FROM payloads ORDER BY rowid").fetchall()
        event_ids = {r[0] for r in rows}
        payload_hashes = {r[1] for r in rows}

        assert len(rows) == 2
        assert len(event_ids) == 2  # one payload row per event
        # Content-addressing still holds: identical content -> identical hash. The hash is
        # simply no longer the IDENTITY of the row.
        assert len(payload_hashes) == 1

        # And the log still replays.
        log = storage.read_all_events(conn)
        replayed = projection.project(
            log,
            as_of=log[-1][0].recorded_at,
            projector_version="0",
        )
        assert replayed[BELIEF_ID]["current_value"] == "64GB"
    finally:
        conn.close()
