"""ADR 0014 stage one: snapshot -> complete ordinary-event delta.

This version retains the skeleton's belief-scoped values and verification.
Identity records, candidates and recorded identity output IDs are later stages.
No subject/property mapping is inferred from opaque skeleton belief IDs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Mapping

from . import hashing
from .events import CORRECTION_APPENDED, Envelope

PROJECTOR_VERSION = "1"


@dataclass(frozen=True, init=False)
class Snapshot:
    """Detached, read-only logical prefix under one projector version.

    Accessors return decoded copies, so callers cannot mutate the snapshot,
    including through nested values. Storage constructs it in one transaction;
    replay constructs the same logical records from its in-memory prefix.
    """

    projector_version: str
    log_position: int
    event_id: str | None
    _beliefs: Mapping[str, str]

    def __init__(self, beliefs: Mapping[str, dict], log_position: int = 0,
                 event_id: str | None = None, projector_version: str = PROJECTOR_VERSION):
        object.__setattr__(self, "projector_version", projector_version)
        object.__setattr__(self, "log_position", log_position)
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "_beliefs", MappingProxyType({
            key: hashing.canonical_json(value) for key, value in beliefs.items()
        }))

    def belief(self, belief_id: str) -> dict | None:
        raw = self._beliefs.get(belief_id)
        return None if raw is None else json.loads(raw)

    def beliefs(self) -> dict[str, dict]:
        return {key: json.loads(self._beliefs[key]) for key in sorted(self._beliefs)}

    def events(self) -> list[dict]:
        return hashing.canonical_set([
            dependency for belief in self.beliefs().values()
            for dependency in belief["event_dependencies"]
        ])

    def event(self, event_id: str) -> dict | None:
        return next((event for event in self.events()
                     if event["event_id"] == event_id), None)


@dataclass(frozen=True)
class EventDelta:
    """All semantic changes for one event; progress is the caller's concern."""

    event_id: str
    beliefs: dict[str, dict[str, Any]]


def reduce(snapshot: Snapshot, envelope: Envelope, payload: dict,
           as_of: str) -> EventDelta:
    """Pure ordinary-event reduction against the complete pre-event snapshot."""
    from .projection import (
        _instant, _RESOLUTION_BASIS, _VALUE_SETTING, _state_for_origin,
        assert_not_backdated,
    )
    if snapshot.projector_version != PROJECTOR_VERSION:
        raise ValueError("snapshot projector version does not match reducer")
    if envelope.event_type not in _VALUE_SETTING:
        raise NotImplementedError(
            f"reducer handler for {envelope.event_type!r} is outside ADR 0014 stage one"
        )
    _instant(as_of, "as_of")
    _instant(envelope.occurred_at)
    state = _state_for_origin(envelope.origin_type)
    belief_id = payload["belief_id"]
    prior = snapshot.belief(belief_id)
    assert_not_backdated(prior, envelope.event_type, envelope.occurred_at)
    if prior is not None and _instant(envelope.occurred_at) < _instant(prior["value_occurred_at"]):
        result = dict(prior)
    else:
        result = {
            "belief_id": belief_id,
            "current_value": payload["value"],
            "value_occurred_at": envelope.occurred_at,
            "verification_state": state,
            "verifiability": payload["verifiability"],
            "display_origin": envelope.origin_type,
            "resolution_basis": _RESOLUTION_BASIS[envelope.event_type],
        }
    for pool in ("supporting_events", "opposing_events", "superseding_events"):
        members = [] if prior is None else list(prior[pool])
        if pool == "supporting_events" or (
            pool == "superseding_events" and envelope.event_type == CORRECTION_APPENDED
        ):
            members.append(envelope.event_id)
        result[pool] = hashing.canonical_set(members)

    # Retain the recorded claims, source information, times, and event hashes
    # behind all evidence pools, including observations older than the head.
    # These are ordinary observation/correction records, not conflict candidates.
    dependencies = {} if prior is None else {
        record["event_id"]: record for record in prior["event_dependencies"]
    }
    if envelope.event_id in dependencies:
        raise ValueError("event already present in pre-event snapshot")
    dependencies[envelope.event_id] = {
        "event_id": envelope.event_id, "event_hash": envelope.event_hash,
        "envelope": asdict(envelope), "payload": json.loads(hashing.canonical_json(payload)),
    }
    result["event_dependencies"] = hashing.canonical_set(list(dependencies.values()))
    result["projected_as_of"] = as_of
    result["updated_at"] = envelope.recorded_at
    predecessors = [] if prior is None else [{
        "belief_id": belief_id, "view_version_hash": prior["view_version_hash"],
    }]
    record = hashing.belief_lineage(
        PROJECTOR_VERSION, envelope.event_id, envelope.event_hash, predecessors, result,
    )
    result["view_version_hash"] = hashing._sha256_hex(hashing.canonical_json(record))
    return EventDelta(envelope.event_id, {belief_id: result})


@dataclass(frozen=True)
class ReducerProjector:
    """Registry entry distinguishing the snapshot boundary from legacy folds."""

    def reduce(self, snapshot: Snapshot, envelope: Envelope, payload: dict,
               as_of: str) -> EventDelta:
        return reduce(snapshot, envelope, payload, as_of)
