"""Walking skeleton — the single vertical slice that is Phase 1's acceptance bar.

spec/NYX_V0_IMPLEMENTATION.md §6. NOT "build the immune system." One event, end
to end, before anything is built wide:

    1. Submit one observation_recorded event (simplest origin type — no affect-split).
    2. Immune Stage 1 ONLY (schema validation); Stages 2–4 stubbed.
    3. Append to `events` (idempotency key enforced, hash chain computed).
    4. Delta-reducer folds it into `resolved_beliefs` (view_version_hash computed).
    5. Read it back; a fresh full-replay fold produces an identical hash.

Acceptance test (implement TEST-FIRST in commit 2, spec §6):

    GIVEN a fresh database
    WHEN an observation_recorded event for "legion.ram = 64GB" is submitted
    THEN events contains exactly 1 row with a valid event_hash
    AND resolved_beliefs shows belief_id="entity:legion/property:ram",
        current_value="64GB", verification_state="verified",
        verifiability="externally_checkable"
    AND replaying the full events log from empty produces an identical view_version_hash
    AND resubmitting the exact same event (same idempotency_key) does not create a second row
    AND attempting UPDATE on events raises an error (trigger enforcement, Invariant 1)

This function is deliberately unimplemented in the scaffold. It is the seam the
walking skeleton drives through — write the test first, then the minimum code in
ids/hashing/events/immune/storage/projection to make THIS pass. Nothing else.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import immune, projection, storage
from .events import OBSERVATION_RECORDED, ORIGIN_OBSERVED, build_event


def record_observation(db_path: str | Path, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Drive one observation_recorded event through immune Stage 1 → append → fold,
    and return the resolved belief. The one seam of the walking skeleton (§6).

    Path: immune Stage 1 (schema validation) → build hashed envelope+payload →
    safe_append_event (idempotency + hash chain + synchronous index) → delta-reducer
    fold into resolved_beliefs → read back. Stages 2–4 and every other event type
    are out of this slice.
    """
    result = immune.stage1_schema_validate(observation)
    if not result.accepted:
        # Rejections should ultimately be logged events (§3); the reject-and-RECORD
        # path is a later slice (§8). The skeleton's happy path never rejects.
        raise ValueError(f"immune stage 1 rejected input: {result.reason}")

    conn = storage.init_db(db_path)
    try:
        payload = {
            "belief_id": observation["belief_id"],
            "value": observation["value"],
            "verifiability": observation["verifiability"],
        }
        envelope, payload_row = build_event(
            event_type=OBSERVATION_RECORDED,
            origin_type=ORIGIN_OBSERVED,
            source=observation["source"],
            source_class=observation["source_class"],
            occurred_at=observation["occurred_at"],
            payload=payload,
            prev_event_hash=storage.last_event_hash(conn),
        )
        appended = storage.safe_append_event(conn, envelope, payload_row)
        if appended:
            prior = storage.read_belief(conn, payload["belief_id"])
            storage.upsert_belief(conn, projection.fold(prior, envelope, payload))
        return storage.read_belief(conn, payload["belief_id"])
    finally:
        conn.close()
