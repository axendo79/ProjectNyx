"""Walking-skeleton acceptance test — spec/NYX_V0_IMPLEMENTATION.md §6.

This test is written FIRST (commit 2 is test-first). It is a literal encoding of
the GIVEN/WHEN/THEN block at §6 lines 243-251:

    GIVEN a fresh database
    WHEN an observation_recorded event for "legion.ram = 64GB" is submitted
    THEN events contains exactly 1 row with a valid event_hash
    AND resolved_beliefs shows belief_id="entity:legion/property:ram",
        current_value="64GB", verification_state="verified",
        verifiability="externally_checkable"
    AND replaying the full events log from empty produces an identical view_version_hash
    AND resubmitting the exact same event (same idempotency_key) does not create a second row
    AND attempting UPDATE on events raises an error (trigger enforcement, Invariant 1)

The path exercised: immune Stage 1 (schema validation) -> append (idempotency +
hash chain) -> delta-reducer fold -> read back -> full-replay hash match.
Nothing wider: one event through the core seam.
"""

from __future__ import annotations

import sqlite3

import pytest

from nyx import projection, storage
from nyx.skeleton import record_observation

# The single observation the skeleton drives (spec §6: "legion.ram = 64GB",
# simplest origin type — a direct observation, no affect-split complexity).
OBSERVATION = {
    "belief_id": "entity:legion/property:ram",
    "value": "64GB",
    "verifiability": "externally_checkable",
    "occurred_at": "2026-07-12T00:00:00+00:00",
    "source": {"actor_id": "sensor:hwscan", "config": {}},
    "source_class": "direct_observation",
}


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "nyx.db")


def test_single_row_with_valid_event_hash(db_path):
    """THEN events contains exactly 1 row with a valid event_hash."""
    record_observation(db_path, OBSERVATION)
    conn = storage.init_db(db_path)
    rows = conn.execute("SELECT event_id, event_type, event_hash FROM events").fetchall()
    assert len(rows) == 1
    event_id, event_type, event_hash = rows[0]
    assert event_type == "observation_recorded"
    assert isinstance(event_hash, str) and len(event_hash) == 64  # sha256 hex
    conn.close()


def test_resolved_belief_fields(db_path):
    """AND resolved_beliefs shows the expected belief."""
    belief = record_observation(db_path, OBSERVATION)
    assert belief["belief_id"] == "entity:legion/property:ram"
    assert belief["current_value"] == "64GB"
    assert belief["verification_state"] == "verified"
    assert belief["verifiability"] == "externally_checkable"

    # ...and it is what actually got materialized in the table, not just returned.
    conn = storage.init_db(db_path)
    row = conn.execute(
        "SELECT current_value, verification_state, verifiability, view_version_hash "
        "FROM resolved_beliefs WHERE belief_id = ?",
        ("entity:legion/property:ram",),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "64GB"
    assert row[1] == "verified"
    assert row[2] == "externally_checkable"
    assert isinstance(row[3], str) and len(row[3]) == 64


def test_full_replay_hash_matches(db_path):
    """AND replaying the full events log from empty produces an identical
    view_version_hash (fold == replay-from-genesis, the executable invariant)."""
    record_observation(db_path, OBSERVATION)
    conn = storage.init_db(db_path)

    materialized = conn.execute(
        "SELECT view_version_hash FROM resolved_beliefs WHERE belief_id = ?",
        ("entity:legion/property:ram",),
    ).fetchone()[0]

    log = storage.read_all_events(conn)
    replayed_view = projection.project(
        log,
        as_of=log[-1][0].recorded_at,
        projector_version="0",
    )
    conn.close()
    assert replayed_view["entity:legion/property:ram"]["view_version_hash"] == materialized


def test_idempotent_resubmit_no_second_row(db_path):
    """AND resubmitting the exact same event (same idempotency_key) does not
    create a second row."""
    record_observation(db_path, OBSERVATION)
    record_observation(db_path, dict(OBSERVATION))  # byte-identical resubmit
    conn = storage.init_db(db_path)
    count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    assert count == 1


def test_update_on_events_is_blocked(db_path):
    """AND attempting UPDATE on events raises an error (trigger enforcement,
    Invariant 1 — append-only is a mechanism, not a convention)."""
    record_observation(db_path, OBSERVATION)
    conn = storage.init_db(db_path)
    # RAISE(ABORT, ...) in the append-only trigger surfaces as IntegrityError.
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE events SET event_type = 'tampered'")
    conn.close()
