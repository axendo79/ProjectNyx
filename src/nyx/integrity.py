"""Validate the existing Layer A schema and hash contract without rewriting bytes."""

import json
from dataclasses import asdict
from datetime import datetime

from . import SCHEMA_VERSION, events, hashing

EVENT_TYPES = frozenset((
    events.CLAIM_ASSERTED, events.OBSERVATION_RECORDED, events.CORRECTION_APPENDED,
    events.CLAIM_QUESTIONED, events.CLAIM_QUARANTINED, events.CLAIM_RESTORED,
    events.GAP_RECORDED, events.SCOPE_MUTATED, events.VERIFICATION_REQUESTED,
    events.VERIFICATION_COMPLETED, events.ENTITY_MENTION_RECORDED,
    events.ENTITY_LINK_PROPOSED, events.ENTITY_LINK_ACCEPTED,
    events.ENTITY_MERGE_ACCEPTED, events.ENTITY_SPLIT_ASSERTED, events.REDACTION_APPLIED,
))
ORIGINS = frozenset((events.ORIGIN_OBSERVED, events.ORIGIN_USER_STATED,
                    events.ORIGIN_VERIFIED_EXTERNAL, events.ORIGIN_DERIVED,
                    events.ORIGIN_PERSONAL))


class IntegrityError(ValueError):
    """Stored or submitted data does not satisfy its committed contract."""


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise IntegrityError(f"{name} must be a nonempty string")


def _hash(value, name):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise IntegrityError(f"{name} must be a SHA-256 hex digest")


def _json(raw, name):
    if not isinstance(raw, str):
        raise IntegrityError(f"{name} must contain JSON text")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise IntegrityError(f"invalid {name} JSON") from exc


def validate_envelope(envelope):
    if not isinstance(envelope, events.Envelope):
        raise IntegrityError("expected an event envelope")
    if envelope.schema_version != SCHEMA_VERSION:
        raise IntegrityError(f"unsupported event schema_version: {envelope.schema_version!r}")
    if envelope.event_type not in EVENT_TYPES:
        raise NotImplementedError(f"unsupported event_type: {envelope.event_type!r}")
    if envelope.origin_type not in ORIGINS:
        raise IntegrityError(f"unknown origin_type: {envelope.origin_type!r}")
    for name in ("event_id", "source_class", "occurred_at", "recorded_at"):
        _text(getattr(envelope, name), name)
    for name in ("occurred_at", "recorded_at"):
        try:
            parsed = datetime.fromisoformat(getattr(envelope, name))
        except ValueError as exc:
            raise IntegrityError(f"invalid {name}") from exc
        if parsed.tzinfo is None:
            raise IntegrityError(f"{name} must carry a timezone offset")
    source = _json(envelope.source, "source")
    if not isinstance(source, dict):
        raise IntegrityError("source must be an object")
    _text(source.get("actor_id"), "source.actor_id")
    if "config" in source and not isinstance(source["config"], dict):
        raise IntegrityError("source.config must be an object")
    if envelope.entity_refs is not None:
        refs = _json(envelope.entity_refs, "entity_refs")
        if not isinstance(refs, list):
            raise IntegrityError("entity_refs must be an array")
        for ref in refs:
            _text(ref, "entity reference")
    for name in ("idempotency_key", "payload_hash", "event_hash"):
        _hash(getattr(envelope, name), name)
    if envelope.prev_event_hash is not None:
        _hash(envelope.prev_event_hash, "prev_event_hash")
    material = asdict(envelope)
    del material["event_hash"], material["prev_event_hash"]
    if hashing.event_hash(material, envelope.prev_event_hash) != envelope.event_hash:
        raise IntegrityError("envelope hash mismatch")


def validate_event(envelope, data):
    validate_envelope(envelope)
    if not isinstance(data, dict):
        raise IntegrityError("event payload must be an object; redaction is unsupported")
    if hashing._sha256_hex(hashing.canonical_json(data)) != envelope.payload_hash:
        raise IntegrityError("payload hash mismatch")
    source = json.loads(envelope.source)
    if hashing.idempotency_key(source["actor_id"], envelope.occurred_at, data) != envelope.idempotency_key:
        raise IntegrityError("idempotency key does not match submitted contents")


def decode_payload(envelope, payload):
    if payload is None or payload.event_id is None:
        raise IntegrityError(f"missing payload row for {envelope.event_id!r}")
    if payload.event_id != envelope.event_id or payload.payload_hash != envelope.payload_hash:
        raise IntegrityError("envelope/payload identity or hash mismatch")
    if payload.redacted:
        raise NotImplementedError("redacted payload replay is not implemented")
    if payload.ciphertext is None:
        raise IntegrityError(f"missing payload content for {envelope.event_id!r}")
    data = _json(payload.ciphertext, "payload")
    validate_event(envelope, data)
    return data


def verified_log(entries, previous_hash=None, previous_recorded_at=None):
    """Verify a full log from genesis, or a suffix from its caller-checked anchor."""
    identifiers, retries = set(), set()
    for envelope, data in entries:
        validate_event(envelope, data)
        if envelope.prev_event_hash != previous_hash:
            raise IntegrityError("event predecessor does not match the preceding log event")
        recorded = datetime.fromisoformat(envelope.recorded_at)
        if previous_recorded_at is not None and recorded < previous_recorded_at:
            raise IntegrityError("recorded_at precedes previous event")
        if envelope.event_id in identifiers or envelope.idempotency_key in retries:
            raise IntegrityError("duplicate event identity in replay")
        identifiers.add(envelope.event_id)
        retries.add(envelope.idempotency_key)
        previous_hash, previous_recorded_at = envelope.event_hash, recorded
        yield envelope, data
