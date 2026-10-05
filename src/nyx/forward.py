"""Explicit projector 3 (ADR 0034 as bounded by ADR 0035)."""
from dataclasses import dataclass, field
from copy import deepcopy

from . import committed, hashing
from .reducer import ReducerProjector


@dataclass(frozen=True)
class Snapshot(committed.Snapshot):
    projector_version: str = field(default="3", init=False)


class Projector(ReducerProjector):
    def reduce(self, snapshot, envelope, payload, as_of):
        return committed.reduce_ordinary(snapshot, envelope, payload, as_of, "3")


def assert_semantically_equivalent_values(old, new):
    """Compare complete canonical values, removing only section-1a differences."""
    def normalized(value, added_status):
        value = deepcopy(value)
        candidates = list(value["claim_candidates"].values())
        for belief in value["beliefs"].values():
            belief.pop("view_version_hash", None)
            candidates.extend(belief["claim_candidates"])
        for candidate in candidates:
            if added_status and candidate.get("live_status") != "live":
                raise ValueError("transition-free candidate must be live")
            if "live_status" in candidate and candidate["live_status"] != "live":
                raise ValueError("non-live status is not a permitted difference")
            candidate.pop("live_status", None)
        return value
    if hashing.canonical_json(normalized(old, False)) != hashing.canonical_json(normalized(new, True)):
        raise ValueError("projector 2/3 semantic equivalence failed")


def assert_semantically_equivalent(old, new):
    if (old.log_position, old.event_id) != (new.log_position, new.event_id):
        raise ValueError("applied progress differs")
    assert_semantically_equivalent_values(old.complete(), new.complete())


def verify_lineage(log, as_of):
    """Full-content reconstruction checks each version-3 lineage step."""
    from . import projection
    previous = {}
    for position in range(1, len(log) + 1):
        snapshot = projection.project_snapshot(log[:position], as_of, "3")
        envelope = log[position - 1][0]
        if snapshot.log_position != position:
            continue
        for belief_id, belief in snapshot.beliefs().items():
            if envelope.event_id not in [c["event_id"] for c in belief["event_dependencies"]]:
                continue
            if previous.get(belief_id, {}).get("view_version_hash") == belief["view_version_hash"]:
                continue
            roots = committed.full_result_roots(belief)
            prior = previous.get(belief_id)
            record = {
                "lineage_format": "nyx-belief-lineage/3", "projector_version": "3",
                "producing_event": {"event_id": envelope.event_id, "event_hash": envelope.event_hash},
                "predecessors": [] if prior is None else [{"belief_id": belief_id,
                    "view_version_hash": prior["view_version_hash"]}],
                "result": {k: v for k, v in belief.items() if k not in (
                    *committed.COLLECTIONS, "view_version_hash", "projected_as_of")},
                "collection_roots": roots, "result_root": committed.result_root(roots),
            }
            if hashing._sha256_hex(hashing.canonical_json(record)) != belief["view_version_hash"]:
                raise ValueError("projector 3 lineage mismatch")
        previous = snapshot.beliefs()
