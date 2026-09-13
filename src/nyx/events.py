"""Event taxonomy and the envelope/payload types.

spec/NYX_ARCHITECTURE.md §1 (event taxonomy, write path) and Invariant 14
(envelope/payload split). spec/NYX_V0_IMPLEMENTATION.md §4 (schema).

Envelopes are intended to carry non-PII metadata, but these types do not enforce
that policy. The hash chain covers envelope fields, including payload_hash;
payload bytes are verified separately. Payload rows are keyed by event ID
(ADR 0007) and contain plaintext JSON (ADR 0002). Crypto-shredding is not built.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from . import SCHEMA_VERSION
from . import hashing
from .ids import new_event_id
from .timestamps import validate_timestamp

# Event taxonomy — spec/NYX_ARCHITECTURE.md §1. Process-trace records live in a
# SEPARATE store (§7): model-performance facts are not claims about the world.
CLAIM_ASSERTED = "claim_asserted"
OBSERVATION_RECORDED = "observation_recorded"
CORRECTION_APPENDED = "correction_appended"
CLAIM_QUESTIONED = "claim_questioned"
CLAIM_QUARANTINED = "claim_quarantined"
CLAIM_RESTORED = "claim_restored"
GAP_RECORDED = "gap_recorded"
SCOPE_MUTATED = "scope_mutated"
VERIFICATION_REQUESTED = "verification_requested"
VERIFICATION_COMPLETED = "verification_completed"
ENTITY_MENTION_RECORDED = "entity_mention_recorded"
ENTITY_LINK_PROPOSED = "entity_link_proposed"
ENTITY_LINK_ACCEPTED = "entity_link_accepted"
ENTITY_MERGE_ACCEPTED = "entity_merge_accepted"
ENTITY_SPLIT_ASSERTED = "entity_split_asserted"
REDACTION_APPLIED = "redaction_applied"

# Origin types — spec/NYX_ARCHITECTURE.md §2. Immutable per event (Invariant 5).
ORIGIN_OBSERVED = "observed"
ORIGIN_USER_STATED = "user_stated"
ORIGIN_VERIFIED_EXTERNAL = "verified_external"
ORIGIN_DERIVED = "derived"
ORIGIN_PERSONAL = "personal"


@dataclass(frozen=True)
class Envelope:
    """Immutable event envelope — the hash chain covers these fields only.

    Field set mirrors the `events` table (spec/NYX_V0_IMPLEMENTATION.md §4). Frozen
    because an appended envelope is immutable (Invariant 1/5); correction is a new
    event, never an edit.
    """

    event_id: str
    idempotency_key: str
    schema_version: str
    event_type: str
    occurred_at: str      # ISO8601, source time
    recorded_at: str      # ISO8601, ingest time
    source: str           # JSON: {actor_id (opaque), config}
    source_class: str
    origin_type: str
    payload_hash: str
    entity_refs: str | None
    prev_event_hash: str | None
    event_hash: str


@dataclass(frozen=True)
class Payload:
    """Separately stored payload with a committed content hash.

    `ciphertext` currently holds plaintext JSON. The schema reserves redaction
    fields, but replay refuses redacted payloads; no REDACTED sentinel or
    crypto-shredding implementation ships.
    """

    payload_hash: str
    event_id: str
    canonical_entity_id: str | None
    ciphertext: str | None
    redacted: bool = False


def build_event(
    *,
    event_type: str,
    origin_type: str,
    source: Mapping[str, Any],
    source_class: str,
    occurred_at: str,
    payload: Mapping[str, Any],
    prev_event_hash: str | None,
    entity_refs: list[str] | None = None,
    event_id: str | None = None,
    recorded_at: str | None = None,
) -> tuple[Envelope, Payload]:
    """Assemble a hashed (Envelope, Payload) pair ready for append.

    Allocates missing IDs and recording times and hashes the supplied semantic
    payload. This helper does not implement extraction or affect routing.
    Append validates the resulting pair against the schema and hash contract.
    """
    validate_timestamp(occurred_at)
    if recorded_at is not None:
        validate_timestamp(recorded_at, "recorded_at")
    source_str = hashing.canonical_json(source)
    entity_refs_str = hashing.canonical_json(entity_refs) if entity_refs is not None else None
    payload_hash = hashing.canonical_json(payload)
    payload_hash = hashing._sha256_hex(payload_hash)

    envelope_minus_hash = {
        "event_id": new_event_id() if event_id is None else event_id,
        "idempotency_key": hashing.idempotency_key(source["actor_id"], occurred_at, payload),
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": datetime.now(timezone.utc).isoformat() if recorded_at is None else recorded_at,
        "source": source_str,
        "source_class": source_class,
        "origin_type": origin_type,
        "payload_hash": payload_hash,
        "entity_refs": entity_refs_str,
    }
    digest = hashing.event_hash(envelope_minus_hash, prev_event_hash)

    envelope = Envelope(
        prev_event_hash=prev_event_hash,
        event_hash=digest,
        **envelope_minus_hash,
    )
    # v0: the payload is stored as plaintext canonical JSON in the ciphertext column.
    # At-rest encryption (crypto-shredding, per-canonical-entity key, Invariant 14)
    # is Phase 3 (spec/NYX_ARCHITECTURE.md §12) — deliberately NOT built in the
    # skeleton; the column name is the eventual home for the ciphertext.
    payload_row = Payload(
        payload_hash=payload_hash,
        event_id=envelope.event_id,
        canonical_entity_id=None,
        ciphertext=hashing.canonical_json(payload),
        redacted=False,
    )
    return envelope, payload_row
