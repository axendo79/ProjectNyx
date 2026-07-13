"""Acceptance test for the `correction_appended` fold handler.

Written FIRST (red), per CLAUDE.md's build order and spec/NYX_V0_IMPLEMENTATION.md §6.
The handler is one of §8's open items (line 287: "only `observation_recorded` is
worked above; `correction_appended` ... need the same treatment. The value-recency
guard (§1) applies to all value-setting handlers.").

Semantics under test (decisions/0004, Option A):

  * `correction_appended` is a deliberate, value-setting event carrying a new value
    and a LATER `occurred_at` than the value it corrects. It supersedes the prior
    belief head: `current_value` / `value_occurred_at` become the correction's.
  * The correction event is recorded in a NEW `superseding_events` column — the
    event class Invariant 6 names ("supporting, opposing, superseding, and gap")
    and the §4 schema omitted. The superseded observation STAYS in
    `supporting_events`, untouched: Inv. 6 says verification *adds* to the set and
    "never rewrites a member", so nothing is retagged or moved.
  * The belief head is NEVER left in `verification_state='superseded'`. That row
    holds the live corrected value; its state stays origin-driven (a correction
    does not auto-promote — Inv. 3). `NYX_ARCHITECTURE.md` line 104 (`any ->
    superseded`) reads as a belief-row state transition, which the §4 one-row-per-
    attribute schema cannot express; per the two-file provenance rule (V0 is
    authoritative for schema/how) that row is the bug. See decisions/0004.
  * Order-independence of RESOLVED STATE comes from the existing §1 value-recency
    guard, not from fold order. Folding {observation, correction} in either rowid
    order must yield the same value/state/support set.

NOT under test (flagged in decisions/0004, deliberately unbuilt): a *backdated*
correction (occurred_at older than the value it corrects), and the origin -> state
mapping for origins other than `observed`.
"""

from __future__ import annotations

import sqlite3

import pytest

from nyx import projection, storage
from nyx.projection import BackdatedCorrectionError
from nyx.skeleton import record_correction, record_observation

BELIEF_ID = "entity:legion/property:ram"

# The original observation: a hardware scan reads 64GB at T1.
OBSERVATION = {
    "belief_id": BELIEF_ID,
    "value": "64GB",
    "verifiability": "externally_checkable",
    "occurred_at": "2026-07-12T00:00:00+00:00",
    "source": {"actor_id": "sensor:hwscan", "config": {}},
    "source_class": "direct_observation",
}

# The correction: a later re-scan establishes the true value is 128GB. Same origin
# class as the observation (`observed`) — deliberately, so this slice tests the
# correction MECHANIC and does not smuggle in a new origin -> state rule for
# `user_stated` et al. (that mapping is an open gap; see decisions/0004).
CORRECTION = {
    "belief_id": BELIEF_ID,
    "value": "128GB",
    "verifiability": "externally_checkable",
    "occurred_at": "2026-07-12T09:30:00+00:00",  # LATER than the observation
    "source": {"actor_id": "sensor:hwscan", "config": {}},
    "source_class": "direct_observation",
}


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "nyx.db")


def _logical(conn: sqlite3.Connection, event_ids: list[str]) -> set[tuple[str, str]]:
    """Resolve event_ids to (event_type, occurred_at) pairs.

    `event_id` is a fresh UUIDv7 per build (ids.py), so the SAME logical event has a
    different id in each database. Comparing support sets ACROSS fold orders is only
    meaningful against something stable — the logical identity of the event.
    """
    rows = conn.execute("SELECT event_id, event_type, occurred_at FROM events").fetchall()
    by_id = {r[0]: (r[1], r[2]) for r in rows}
    return {by_id[eid] for eid in event_ids}


def _fold_in_order(db_path: str, first: dict, second: dict) -> tuple[dict, sqlite3.Connection]:
    """Drive two events through the real write path in the given rowid order.

    Insertion order IS rowid order IS fold order (§1), so calling in sequence is
    exactly "fold in this rowid order". Returns the resolved belief and an open
    connection for inspection.
    """
    record = {"observation_recorded": record_observation, "correction_appended": record_correction}
    for event in (first, second):
        record[event["_event_type"]](db_path, {k: v for k, v in event.items() if k != "_event_type"})
    conn = storage.init_db(db_path)
    return storage.read_belief(conn, BELIEF_ID), conn


OBS = {**OBSERVATION, "_event_type": "observation_recorded"}
CORR = {**CORRECTION, "_event_type": "correction_appended"}


def test_correction_supersedes_prior_value(db_path):
    """A correction supersedes the earlier belief value, and records WHY."""
    record_observation(db_path, OBSERVATION)
    belief = record_correction(db_path, CORRECTION)

    # The head is the corrected value, timestamped by the correction.
    assert belief["current_value"] == "128GB"
    assert belief["value_occurred_at"] == CORRECTION["occurred_at"]

    conn = storage.init_db(db_path)
    try:
        # The correction is a superseding event (Inv. 6's named class).
        assert _logical(conn, belief["superseding_events"]) == {
            ("correction_appended", CORRECTION["occurred_at"])
        }
        # The superseded observation is STILL in the support set, unmoved and
        # unretagged — Inv. 6: verification adds to the set, never rewrites a member.
        assert _logical(conn, belief["supporting_events"]) == {
            ("observation_recorded", OBSERVATION["occurred_at"]),
            ("correction_appended", CORRECTION["occurred_at"]),
        }
    finally:
        conn.close()

    # The live head is NOT parked in `superseded` — that state would describe the
    # value this row no longer holds. State stays origin-driven; a correction does
    # not auto-promote (Inv. 3).
    assert belief["verification_state"] != "superseded"
    assert belief["verification_state"] == "verified"


def test_resolved_state_is_order_independent(tmp_path):
    """Folding {observation, correction} in EITHER rowid order yields the same
    resolved state. The guarantee comes from the §1 value-recency guard, not from
    fold order — this is the reconnection seam (§5 trace 2) applied to corrections.
    """
    forward, conn_f = _fold_in_order(str(tmp_path / "forward.db"), OBS, CORR)
    reverse, conn_r = _fold_in_order(str(tmp_path / "reverse.db"), CORR, OBS)
    try:
        assert forward["current_value"] == reverse["current_value"] == "128GB"
        assert forward["value_occurred_at"] == reverse["value_occurred_at"]
        assert forward["verification_state"] == reverse["verification_state"]
        assert _logical(conn_f, forward["supporting_events"]) == _logical(
            conn_r, reverse["supporting_events"]
        )
        assert _logical(conn_f, forward["superseding_events"]) == _logical(
            conn_r, reverse["superseding_events"]
        )
        # NOTE: `view_version_hash` is deliberately NOT compared across orders. It
        # chains SHA256(prior || event_hash) in rowid order (§1) and is therefore
        # order-dependent BY DESIGN. Making it order-invariant would require a hash
        # redesign that §1 rejects. Equality across orders is asserted on resolved
        # STATE only; hash equality is asserted fold-vs-replay WITHIN an order below.
    finally:
        conn_f.close()
        conn_r.close()


@pytest.mark.parametrize("order", [(OBS, CORR), (CORR, OBS)], ids=["obs-first", "correction-first"])
def test_fold_equals_replay_within_each_order(tmp_path, order):
    """fold == replay-from-genesis, per order (the executable invariant, §12)."""
    path = str(tmp_path / "replay.db")
    belief, conn = _fold_in_order(path, *order)
    try:
        replayed = projection.project(
            storage.read_all_events(conn),
            as_of="2026-07-12T12:00:00+00:00",
            projector_version="0",
        )
        assert replayed[BELIEF_ID]["view_version_hash"] == belief["view_version_hash"]
        # ...and replay agrees on the resolved value too, not just the hash.
        assert replayed[BELIEF_ID]["current_value"] == belief["current_value"]
    finally:
        conn.close()


def test_correction_resubmit_is_idempotent(db_path):
    """Resubmitting the identical correction adds no second row (§1 idempotency)."""
    record_observation(db_path, OBSERVATION)
    record_correction(db_path, CORRECTION)
    record_correction(db_path, dict(CORRECTION))  # byte-identical resubmit

    conn = storage.init_db(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        corrections = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'correction_appended'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert corrections == 1
    assert total == 2  # the observation and exactly one correction


def test_backdated_correction_raises(db_path):
    """A BACKDATED correction (occurred_at OLDER than the value it corrects) fails
    loud. This is an INTERIM fail-loud stance, not a decided semantics: whether such a
    correction is newer-information-governed-by-recency (folds as provenance only) or
    an authoritative override (takes the head regardless of date) is OPEN — see
    decisions/0005. Raising a specific, identifiable type is what keeps the open
    question findable: when the semantics are decided, this test is the thing to
    delete, and `BackdatedCorrectionError` greps straight to every site that assumed it.
    """
    record_observation(db_path, {**OBSERVATION, "occurred_at": "2026-07-12T09:30:00+00:00"})
    backdated = {**CORRECTION, "occurred_at": "2026-07-12T00:00:00+00:00"}  # BEFORE the value
    with pytest.raises(BackdatedCorrectionError):
        record_correction(db_path, backdated)


def test_backdated_correction_does_not_poison_layer_a(db_path):
    """The rejected correction must never reach Layer A.

    Layer A is append-only and engine-enforced (Inv. 1) — an appended event can NEVER
    be removed. So a correction that the fold refuses must be rejected BEFORE the
    append, not after: otherwise the event is durably in the log, every subsequent
    full replay re-folds it, and replay raises forever. An unreplayable log is an
    unrecoverable one (replay is the crash-recovery path, §6).
    """
    record_observation(db_path, {**OBSERVATION, "occurred_at": "2026-07-12T09:30:00+00:00"})
    with pytest.raises(BackdatedCorrectionError):
        record_correction(db_path, {**CORRECTION, "occurred_at": "2026-07-12T00:00:00+00:00"})

    conn = storage.init_db(db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        assert count == 1  # the observation only — the correction never landed

        # The belief is untouched, and the log still replays.
        belief = storage.read_belief(conn, BELIEF_ID)
        assert belief["current_value"] == "64GB"
        assert belief["superseding_events"] == []
        replayed = projection.project(
            storage.read_all_events(conn),
            as_of="2026-07-12T12:00:00+00:00",
            projector_version="0",
        )
        assert replayed[BELIEF_ID]["view_version_hash"] == belief["view_version_hash"]
    finally:
        conn.close()


def test_append_only_triggers_still_hold_with_a_correction(db_path):
    """Layer A stays append-only (Invariant 1) — a correction supersedes, never edits."""
    record_observation(db_path, OBSERVATION)
    record_correction(db_path, CORRECTION)
    conn = storage.init_db(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE events SET event_type = 'tampered'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM events WHERE event_type = 'observation_recorded'")
    finally:
        conn.close()
