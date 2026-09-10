"""Version 1: complete, pure stage-two reduction (ADRs 0013–0024)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Mapping

from . import hashing
from .events import ENTITY_MENTION_RECORDED, OBSERVATION_RECORDED, Envelope

PROJECTOR_VERSION = "1"
RECORD_KINDS = ("beliefs", "entities", "mentions", "entity_links", "claim_candidates", "events")
SUPPORTED_EVENTS = (ENTITY_MENTION_RECORDED, OBSERVATION_RECORDED)


@dataclass(frozen=True, init=False)
class Snapshot:
    """Detached prefix. Lookups are scoped by record kind, never by ID spelling."""

    projector_version: str
    log_position: int
    event_id: str | None
    _records: Mapping[str, Mapping[str, str]]

    def __init__(self, beliefs: Mapping[str, dict], log_position: int = 0,
                 event_id: str | None = None, projector_version: str = PROJECTOR_VERSION,
                 *, entities=None, mentions=None, entity_links=None,
                 claim_candidates=None, events=None):
        object.__setattr__(self, "projector_version", projector_version)
        object.__setattr__(self, "log_position", log_position)
        object.__setattr__(self, "event_id", event_id)
        records = dict(beliefs=beliefs, entities=entities, mentions=mentions,
                       entity_links=entity_links, claim_candidates=claim_candidates, events=events)
        object.__setattr__(self, "_records", MappingProxyType({
            kind: MappingProxyType({key: hashing.canonical_json(value)
                                    for key, value in (rows or {}).items()})
            for kind, rows in records.items()
        }))

    def record(self, kind: str, identifier: str) -> dict | None:
        raw = self._records[kind].get(identifier)
        return None if raw is None else json.loads(raw)

    def records(self, kind: str) -> dict[str, dict]:
        return {key: json.loads(raw) for key, raw in sorted(self._records[kind].items())}

    def complete(self) -> dict:
        return {kind: self.records(kind) for kind in RECORD_KINDS}

    def belief(self, belief_id: str) -> dict | None:
        return self.record("beliefs", belief_id)

    def beliefs(self) -> dict[str, dict]:
        return self.records("beliefs")

    def event(self, event_id: str) -> dict | None:
        return self.record("events", event_id)

    def events(self) -> list[dict]:
        return hashing.canonical_set(list(self.records("events").values()))

    def current_belief(self, subject_id: str, property_id: str) -> dict | None:
        matches = [b for b in self.beliefs().values() if b["lifecycle_status"] == "current"
                   and b["subject_id"] == subject_id and b["property_id"] == property_id]
        if len(matches) > 1:
            raise ValueError("duplicate current belief in snapshot")
        return matches[0] if matches else None

    def apply(self, delta: EventDelta, position: int) -> Snapshot:
        records = self.complete()
        for kind in RECORD_KINDS:
            records[kind].update(getattr(delta, kind))
        return Snapshot(**records, log_position=position, event_id=delta.event_id,
                        projector_version=self.projector_version)


@dataclass(frozen=True)
class EventDelta:
    event_id: str
    beliefs: dict[str, dict] = field(default_factory=dict)
    entities: dict[str, dict] = field(default_factory=dict)
    mentions: dict[str, dict] = field(default_factory=dict)
    entity_links: dict[str, dict] = field(default_factory=dict)
    claim_candidates: dict[str, dict] = field(default_factory=dict)
    events: dict[str, dict] = field(default_factory=dict)


def _fields(record, required):
    if not isinstance(record, dict) or set(record) != set(required):
        raise ValueError(f"record requires exactly these fields: {sorted(required)}")


def _string(record, name):
    value = record[name]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _required(snapshot, kind, identifier):
    record = snapshot.record(kind, identifier)
    if record is None:
        raise ValueError(f"unknown {kind} ID: {identifier!r}")
    return record


def _fresh(snapshot, kind, identifier, created):
    if identifier in created or snapshot.record(kind, identifier) is not None:
        raise ValueError(f"reused {kind} ID: {identifier!r}")


def _entity_refs(envelope, subjects):
    if envelope.entity_refs is not None:
        refs = json.loads(envelope.entity_refs)
        if (not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs)
                or set(refs) != set(subjects)):
            raise ValueError("entity_refs do not match recorded subject associations")


def evidence_event_ids(claim_candidates) -> list[str]:
    """Union count uses event identity, not candidate or path count."""
    return hashing.canonical_set([event_id for c in claim_candidates
                                 for event_id in c["supporting_events"]])


def canonical_claim_candidates(records):
    """One claim identity can have several paths; agreement never joins IDs."""
    by_id = {}
    for record in records:
        candidate = dict(record)
        key = candidate["claim_candidate_id"]
        prior = by_id.get(key)
        if prior is not None:
            if ({k: v for k, v in prior.items() if k != "provenance_paths"}
                    != {k: v for k, v in candidate.items() if k != "provenance_paths"}):
                raise ValueError("inconsistent records for one ClaimCandidate identity")
            candidate["provenance_paths"] = prior["provenance_paths"] + candidate["provenance_paths"]
        candidate["provenance_paths"] = hashing.canonical_set(candidate["provenance_paths"])
        by_id[key] = candidate
    return hashing.canonical_set(list(by_id.values()))


def identity_confidence_ceiling(links):
    """Only bootstrap scoring is decided. No empty-set arithmetic default."""
    for link in links:
        if link["link_state"] != "constitutive":
            raise NotImplementedError("non-constitutive confidence treatment is not decided")
        if link["entity_link_confidence"] is not None:
            raise ValueError("constitutive links have no epistemic confidence")
    return None


def scalar_belief_value(belief):
    if len(belief["claim_candidates"]) > 1:
        raise ValueError("scalar belief request refuses multiple ClaimCandidates (ADR 0024)")
    # ADR 0024 explicitly supplies no additional scalar contract.
    raise NotImplementedError("use a named ClaimCandidate; scalar belief read contract is deferred")


def reduce(snapshot: Snapshot, envelope: Envelope, payload: dict, as_of: str) -> EventDelta:
    from .projection import _instant, _state_for_origin

    if snapshot.projector_version != PROJECTOR_VERSION:
        raise ValueError("snapshot projector version does not match reducer")
    if envelope.event_type not in SUPPORTED_EVENTS:
        raise NotImplementedError(f"stage two refuses {envelope.event_type!r}")
    _instant(as_of, "as_of")
    _instant(envelope.occurred_at)
    _instant(envelope.recorded_at, "recorded_at")
    _string(asdict(envelope), "event_id")
    source = json.loads(envelope.source)
    _string(source, "actor_id")  # Provenance only; supplies no authority policy.
    _string(asdict(envelope), "source_class")
    _fresh(snapshot, "events", envelope.event_id, {})
    dependency = {"event_id": envelope.event_id, "event_hash": envelope.event_hash,
                  "envelope": asdict(envelope),
                  "payload": json.loads(hashing.canonical_json(payload))}
    delta = EventDelta(envelope.event_id, events={envelope.event_id: dependency})
    if envelope.event_type == ENTITY_MENTION_RECORDED:
        _fields(payload, ("mention_id", "subject_id", "text", "link_state"))
        mention_id = _string(payload, "mention_id")
        subject_id = _string(payload, "subject_id")
        _string(payload, "text")
        if payload["link_state"] != "constitutive":
            raise ValueError("bootstrap requires explicit constitutive link_state")
        _fresh(snapshot, "mentions", mention_id, {})
        _fresh(snapshot, "entities", subject_id, {})
        delta.entities[subject_id] = {
            "subject_id": subject_id, "lifecycle_status": "current",
            "constituting_mention_id": mention_id, "event_id": envelope.event_id,
            "predecessors": [],
        }
        delta.mentions[mention_id] = {
            "mention_id": mention_id, "text": payload["text"], "subject_id": subject_id,
            "event_id": envelope.event_id,
        }
        delta.entity_links[mention_id] = {
            "mention_id": mention_id, "subject_id": subject_id,
            "link_state": "constitutive", "entity_link_confidence": None,
            "event_id": envelope.event_id,
        }
        _entity_refs(envelope, [subject_id])
        return delta

    state = _state_for_origin(envelope.origin_type)
    _fields(payload, ("claims",))
    if not isinstance(payload["claims"], list) or not payload["claims"]:
        raise ValueError("observation requires nonempty explicitly scoped claims")
    for claim in payload["claims"]:
        _fields(claim, ("mention_id", "subject_id", "property_id", "belief_id",
                        "claim_candidate_id", "value", "verifiability"))
        for name in ("mention_id", "subject_id", "property_id", "belief_id", "claim_candidate_id"):
            _string(claim, name)
        if claim["verifiability"] not in (
            "externally_checkable", "locally_checkable", "subjective", "structurally_unverifiable"
        ):
            raise ValueError("unknown verifiability")
        subject_id, mention_id = claim["subject_id"], claim["mention_id"]
        entity = _required(snapshot, "entities", subject_id)
        mention = _required(snapshot, "mentions", mention_id)
        link = _required(snapshot, "entity_links", mention_id)
        if entity["lifecycle_status"] != "current" or mention["subject_id"] != subject_id or link["subject_id"] != subject_id:
            raise ValueError("mention/subject association does not match recorded identity")
        identity_confidence_ceiling([link])
        belief_id, candidate_id = claim["belief_id"], claim["claim_candidate_id"]
        _fresh(snapshot, "claim_candidates", candidate_id, delta.claim_candidates)
        current = snapshot.current_belief(subject_id, claim["property_id"])
        if current is not None and current["belief_id"] != belief_id:
            raise ValueError("subject/property already has a current belief; name its existing ID")
        prior = snapshot.belief(belief_id)
        belief = delta.beliefs.get(belief_id, prior)
        if belief is not None:
            if (belief["subject_id"], belief["property_id"], belief["lifecycle_status"]) != (
                subject_id, claim["property_id"], "current"
            ):
                raise ValueError("belief ID has a different subject/property or is historical")
        else:
            if any((b["subject_id"], b["property_id"]) == (subject_id, claim["property_id"])
                   for b in delta.beliefs.values()):
                raise ValueError("duplicate current belief in submitted event")
            belief = {"belief_id": belief_id, "subject_id": subject_id,
                      "property_id": claim["property_id"], "lifecycle_status": "current",
                      "predecessors": [], "claim_candidates": [], "identity_records": [],
                      "event_dependencies": [], "resolution_status": "no_authoritative_head"}
        candidate = {
            **json.loads(hashing.canonical_json(claim)),
            "verification_state": state, "verification_basis": {
                "kind": "direct_observation", "event_ids": [envelope.event_id]},
            "supporting_events": [envelope.event_id], "opposing_events": [],
            "superseding_events": [], "restrictions": [], "predecessors": [],
            "occurred_at": envelope.occurred_at, "recorded_at": envelope.recorded_at,
            "source": source, "source_class": envelope.source_class,
            "origin_type": envelope.origin_type,
            "provenance_paths": [[{"event_id": link["event_id"], "mention_id": mention_id,
                                   "subject_id": subject_id},
                                  {"event_id": envelope.event_id, "belief_id": belief_id,
                                   "claim_candidate_id": candidate_id}]],
        }
        delta.claim_candidates[candidate_id] = candidate
        result = dict(belief)
        result["claim_candidates"] = canonical_claim_candidates(belief["claim_candidates"] + [candidate])
        result["identity_records"] = hashing.canonical_set(belief["identity_records"] + [
            {"entity": entity, "mention": mention, "link": link}])
        result["event_dependencies"] = hashing.canonical_set(belief["event_dependencies"] + [
            dependency, _required(snapshot, "events", link["event_id"])])
        result["projected_as_of"] = as_of
        result["updated_at"] = envelope.recorded_at
        delta.beliefs[belief_id] = result

    _entity_refs(envelope, [b["subject_id"] for b in delta.beliefs.values()])
    for belief_id, result in delta.beliefs.items():
        prior = snapshot.belief(belief_id)
        predecessors = [] if prior is None else [{
            "belief_id": belief_id, "view_version_hash": prior["view_version_hash"]}]
        record = hashing.belief_lineage(PROJECTOR_VERSION, envelope.event_id,
                                       envelope.event_hash, predecessors, result)
        result["view_version_hash"] = hashing._sha256_hex(hashing.canonical_json(record))
    return delta


@dataclass(frozen=True)
class ReducerProjector:
    def reduce(self, snapshot: Snapshot, envelope: Envelope, payload: dict, as_of: str) -> EventDelta:
        return reduce(snapshot, envelope, payload, as_of)
