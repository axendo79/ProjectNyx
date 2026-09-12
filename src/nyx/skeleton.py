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

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import immune, projection, storage
from .events import CORRECTION_APPENDED, OBSERVATION_RECORDED, ORIGIN_OBSERVED, build_event


def _record(db_path: str | Path, event_type: str, submission: Mapping[str, Any],
            projector_version: str = "0") -> dict[str, Any]:
    """Drive one value-setting event through immune Stage 1 → append → fold, and
    return the resolved belief. The one seam of the walking skeleton (§6).

    Path: immune Stage 1 (schema validation) → build hashed envelope+payload →
    safe_append_event (idempotency + hash chain + synchronous index) → delta-reducer
    fold into resolved_beliefs → read back. Stages 2–4 and every other event type
    are out of this slice.

    `observation_recorded` and `correction_appended` share this path verbatim: they
    differ only in the provenance the fold records (§8 — "the value-recency guard
    applies to all value-setting handlers"), never in how they are validated,
    hashed, or appended. A correction is an ordinary append; it supersedes by being
    a later event, never by editing one (Invariant 1).
    """
    storage._registered_projector(projector_version)
    if projector_version in ("1", "2"):
        return _record_stage_two(db_path, event_type, submission, projector_version)
    result = immune.stage1_schema_validate(submission)
    if not result.accepted:
        # Rejections should ultimately be logged events (§3); the reject-and-RECORD
        # path is a later slice (§8). The skeleton's happy path never rejects.
        raise ValueError(f"immune stage 1 rejected input: {result.reason}")

    conn = storage.init_db(db_path)
    try:
        payload = {
            "belief_id": submission["belief_id"],
            "value": submission["value"],
            "verifiability": submission["verifiability"],
        }

        # Read the prior head BEFORE the append — the append is the commit point
        # (Inv. 8) and Layer A is append-only (Inv. 1), so anything the fold would
        # refuse must be refused here, while refusing is still possible. A backdated
        # correction appended and only THEN rejected at fold time would sit in the log
        # permanently, and every future replay would raise on it. See decisions/0005.
        storage.materialize_pending(conn, datetime.now(timezone.utc).isoformat(), projector_version)
        if projector_version == "0":
            prior = storage.read_belief(conn, payload["belief_id"])
            projection.assert_not_backdated(prior, event_type, submission["occurred_at"])

        envelope, payload_row = build_event(
            event_type=event_type,
            origin_type=ORIGIN_OBSERVED,
            source=submission["source"],
            source_class=submission["source_class"],
            occurred_at=submission["occurred_at"],
            payload=payload,
            prev_event_hash=storage.last_event_hash(conn),
        )
        storage.safe_append_event(conn, envelope, payload_row, projector_version)
        # Separate derived transaction, including retries after an append
        # committed but publication/worker acknowledgement did not finish.
        # Evaluation time belongs to the caller (ADR 0010 section 3b).
        storage.materialize_pending(conn, datetime.now(timezone.utc).isoformat(), projector_version)
        return storage.read_belief(conn, payload["belief_id"], projector_version)
    finally:
        conn.close()


def record_observation(db_path: str | Path, observation: Mapping[str, Any],
                       projector_version: str = "0") -> dict[str, Any]:
    """Record one `observation_recorded` event and return the resolved belief (§6)."""
    return _record(db_path, OBSERVATION_RECORDED, observation, projector_version)


def _record_stage_two(db_path, event_type, recorded_event, projector_version="1"):
    from . import ingestion
    from .events import ENTITY_MENTION_RECORDED, Envelope, Payload
    if event_type not in (OBSERVATION_RECORDED, ENTITY_MENTION_RECORDED):
        raise NotImplementedError(f"stage two refuses {event_type!r}")
    if (not isinstance(recorded_event, tuple) or len(recorded_event) != 2
            or not isinstance(recorded_event[0], Envelope) or not isinstance(recorded_event[1], Payload)):
        raise ValueError(f"version {projector_version} requires a retained Envelope/Payload pair from nyx.ingestion")
    if recorded_event[0].event_type != event_type:
        raise ValueError("recorded event type does not match writer operation")
    conn = storage.init_db(db_path)
    try:
        ingestion.submit(conn, recorded_event, datetime.now(timezone.utc).isoformat(), projector_version)
        import json
        payload = json.loads(recorded_event[1].ciphertext)
        if event_type == ENTITY_MENTION_RECORDED:
            return storage.read_mention(conn, payload["mention_id"], projector_version)
        return {claim["belief_id"]: storage.read_belief(conn, claim["belief_id"], projector_version)
                for claim in payload["claims"]}
    finally:
        conn.close()


def record_mention(db_path, recorded_event, projector_version="1"):
    """Submit one retained entity_mention_recorded event under the selected version."""
    from .events import ENTITY_MENTION_RECORDED
    return _record_stage_two(db_path, ENTITY_MENTION_RECORDED, recorded_event, projector_version)


def record_correction(db_path: str | Path, correction: Mapping[str, Any],
                      projector_version: str = "0") -> dict[str, Any]:
    """Record one `correction_appended` event and return the resolved belief.

    The correction carries a NEW value and a LATER `occurred_at` than the value it
    corrects; it supersedes the prior belief head. A *backdated* correction (older
    `occurred_at` than the value it corrects) is deliberately NOT built: it would fold
    through the §1 value-recency guard as provenance only, which is very likely the
    wrong semantics for a deliberate authoritative correction — but the right
    semantics have not been decided. Flagged as an open gap in decisions/0004; do not
    infer the behaviour from what this code happens to do.
    """
    return _record(db_path, CORRECTION_APPENDED, correction, projector_version)
