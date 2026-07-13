"""`occurred_at` ordering is INSTANT-based, not lexical.

Red-first. Every value-setting decision in the system rests on comparing `occurred_at`
against `resolved_beliefs.value_occurred_at`:

  * the §1 value-recency guard (does this event supersede the current value, or fold as
    provenance only?) — `projection.fold`
  * the backdated-correction refusal (decisions/0005) — `projection.assert_not_backdated`

Both compare raw ISO8601 STRINGS. Lexical order over ISO8601 text is NOT chronological
order once offsets vary: the same instant has many spellings (`Z` vs `+00:00`), and a
non-UTC offset can make a later instant sort earlier (and vice versa). The guard is
therefore corruptible in BOTH directions — it can refuse a valid correction as
"backdated", and it can silently accept a genuinely backdated one and let it take the
head.

This passed every existing test only because every fixture used one fixed format
(`+00:00`, UTC). That is a latent corruption, not a working comparison: the tests agreed
with the bug because they never varied the thing the bug depends on.
"""

from __future__ import annotations

import pytest

from nyx import storage
from nyx.projection import BackdatedCorrectionError
from nyx.skeleton import record_correction, record_observation

BELIEF_ID = "entity:legion/property:ram"

_BASE = {
    "belief_id": BELIEF_ID,
    "verifiability": "externally_checkable",
    "source": {"actor_id": "sensor:hwscan", "config": {}},
    "source_class": "direct_observation",
}


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "nyx.db")


def _read(db_path: str) -> dict:
    conn = storage.init_db(db_path)
    try:
        return storage.read_belief(conn, BELIEF_ID)
    finally:
        conn.close()


def test_later_instant_written_with_a_negative_offset_supersedes(db_path):
    """A correction at a LATER instant must supersede — even when its ISO text sorts
    EARLIER than the value it corrects.

        observation  2026-07-12T12:00:00Z       -> instant 12:00Z
        correction   2026-07-12T09:00:00-05:00  -> instant 14:00Z  (TWO HOURS LATER)

    Lexically "09:00:00-05:00" < "12:00:00Z", so a string comparison reads the
    correction as backdated and REFUSES it (decisions/0005). Chronologically it is the
    newer value and must take the head.
    """
    record_observation(db_path, {**_BASE, "value": "64GB", "occurred_at": "2026-07-12T12:00:00Z"})
    record_correction(
        db_path, {**_BASE, "value": "128GB", "occurred_at": "2026-07-12T09:00:00-05:00"}
    )
    belief = _read(db_path)
    assert belief["current_value"] == "128GB"


def test_earlier_instant_written_with_a_positive_offset_is_still_backdated(db_path):
    """The opposite corruption, and the more dangerous one: a correction at an EARLIER
    instant must still be refused — even when its ISO text sorts LATER.

        observation  2026-07-12T12:00:00Z       -> instant 12:00Z
        correction   2026-07-12T13:00:00+05:00  -> instant 08:00Z  (FOUR HOURS EARLIER)

    Lexically "13:00:00+05:00" > "12:00:00Z", so a string comparison reads the
    correction as newer, sails past the backdated check, and lets it take the head —
    the exact silent wrong answer decisions/0005 exists to prevent.
    """
    record_observation(db_path, {**_BASE, "value": "64GB", "occurred_at": "2026-07-12T12:00:00Z"})
    with pytest.raises(BackdatedCorrectionError):
        record_correction(
            db_path, {**_BASE, "value": "128GB", "occurred_at": "2026-07-12T13:00:00+05:00"}
        )
    assert _read(db_path)["current_value"] == "64GB"


def test_same_instant_spelled_two_ways_compares_equal(db_path):
    """`Z` and `+00:00` are the SAME instant and must compare as such.

    Lexically they do not: '+' (0x2B) sorts before 'Z' (0x5A), so "...+00:00" reads as
    strictly EARLIER than "...Z". A second value-setting event at the same instant would
    then fold as provenance-only and fail to update the value — purely because of how its
    timestamp was spelled.

    The guard is a strict `<`, so equal instants are not "older": the later-folded event
    takes the value. This asserts that behaviour is IDENTICAL across spellings.
    """
    record_observation(db_path, {**_BASE, "value": "64GB", "occurred_at": "2026-07-12T00:00:00Z"})
    record_observation(
        db_path, {**_BASE, "value": "128GB", "occurred_at": "2026-07-12T00:00:00+00:00"}
    )
    belief = _read(db_path)
    assert belief["current_value"] == "128GB"
    assert len(belief["supporting_events"]) == 2
