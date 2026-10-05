"""Explicit projector 3 (ADR 0034 as bounded by ADR 0035)."""
from dataclasses import asdict, dataclass, field
from copy import deepcopy

from . import committed, hashing, integrity, merkle, transition_dependencies
from .events import CORRECTION_APPENDED, CANDIDATE_REPLACED, CANDIDATE_EXPIRED
from .reducer import ReducerProjector, _fields, _string, _required, _fresh, _entity_refs

TRANSITIONS = {CORRECTION_APPENDED: ("corrected", "corrected_by"),
               CANDIDATE_REPLACED: ("replaced", "replaced_by"),
               CANDIDATE_EXPIRED: ("expired", "expired_at")}


@dataclass(frozen=True)
class Snapshot(committed.Snapshot):
    projector_version: str = field(default="3", init=False)

    def relations(self):
        """Reconstruct indexed ending relations from the committed event chain."""
        pending = {entry["envelope"]["prev_event_hash"]: entry for entry in self.events()}
        previous, result = None, {}
        for position in range(1, self.log_position + 1):
            entry = pending[previous]
            envelope, payload = entry["envelope"], entry["payload"]
            if envelope["event_type"] in TRANSITIONS:
                for target in payload["targets"]:
                    result[target] = {"target_candidate_id": target, "event_id": envelope["event_id"],
                        "relation": TRANSITIONS[envelope["event_type"]][1], "log_position": position}
            previous = envelope["event_hash"]
        return result

    def candidate_sets(self, belief_id):
        belief = self.belief(belief_id)
        if belief is None:
            return None
        relations = self.relations()
        live, retained = [], []
        for candidate in belief["claim_candidates"]:
            ending = relations.get(candidate["claim_candidate_id"])
            validate_ending(candidate, ending)
            if ending is None:
                live.append(candidate)
            else:
                retained.append({"candidate": candidate, "ending_relation": ending})
        return {"live": live, "retained": retained}


@dataclass(frozen=True)
class Delta(committed.Delta):
    relations: dict = field(default_factory=dict)


def validate_ending(candidate, ending):
    if ending is None:
        if candidate["live_status"] != "live" or candidate["superseding_events"]:
            raise ValueError("candidate ending relation is missing")
    else:
        statuses = {relation: status for status, relation in TRANSITIONS.values()}
        if (candidate["live_status"] != statuses.get(ending["relation"])
                or candidate["superseding_events"] != [ending["event_id"]]):
            raise ValueError("candidate differs from ending relation")


class Projector(ReducerProjector):
    def reduce(self, snapshot, envelope, payload, as_of):
        if envelope.event_type in TRANSITIONS:
            return reduce_transition(snapshot, envelope, payload, as_of)
        return committed.reduce_ordinary(snapshot, envelope, payload, as_of, "3")


def reduce_transition(snapshot, envelope, payload, as_of):
    from .projection import _instant, BackdatedCorrectionError
    if not isinstance(snapshot, Snapshot) or snapshot.projector_version != "3":
        raise ValueError("snapshot projector version does not match reducer")
    integrity.validate_event(envelope, payload)
    _instant(as_of, "as_of")
    _instant(envelope.recorded_at, "recorded_at")
    occurred = _instant(envelope.occurred_at)
    _fresh(snapshot, "events", envelope.event_id, {})
    if envelope.event_type == CANDIDATE_EXPIRED:
        _fields(payload, ("belief_id", "targets", "basis"))
        claim = None
        belief_id = _string(payload, "belief_id")
    else:
        _fields(payload, ("claim", "targets", "basis"))
        claim = payload["claim"]
        _fields(claim, ("mention_id", "subject_id", "property_id", "belief_id",
                        "claim_candidate_id", "value", "verifiability"))
        belief_id = _string(claim, "belief_id")
        _fresh(snapshot, "claim_candidates", _string(claim, "claim_candidate_id"), {})
    _fields(payload["basis"], ("kind", "statement"))
    basis_kind = "stated_error" if envelope.event_type == CORRECTION_APPENDED else "stated"
    if payload["basis"]["kind"] != basis_kind:
        raise ValueError(f"transition requires {basis_kind} basis")
    _string(payload["basis"], "statement")
    targets = payload["targets"]
    if (not isinstance(targets, list) or not targets
            or any(not isinstance(target, str) or not target for target in targets)
            or targets != sorted(set(targets))):
        raise ValueError("targets require nonempty distinct canonically sorted IDs")
    belief = snapshot.header(belief_id)
    if belief is None or belief["lifecycle_status"] != "current":
        raise ValueError("targets require one current belief")
    candidates = []
    for target in targets:
        candidate = _required(snapshot, "claim_candidates", target)
        if candidate["live_status"] != "live":
            raise ValueError("target candidate is no longer live")
        if (candidate["belief_id"], candidate["subject_id"], candidate["property_id"]) != (
                belief_id, belief["subject_id"], belief["property_id"]):
            raise ValueError("targets must share the exact belief scope")
        if "report_vocabulary" in candidate["source"]["config"]:
            raise NotImplementedError("report-scoped transitions refuse under ADR 0035 section 3")
        if envelope.event_type == CORRECTION_APPENDED:
            recorded = _required(snapshot, "events", candidate["supporting_events"][0])
            if occurred < _instant(recorded["envelope"]["occurred_at"]):
                raise BackdatedCorrectionError("correction occurred_at precedes target recording event")
        candidates.append(candidate)
    transition_dependencies.check_transition_dependencies(snapshot, targets)
    dependency = {"event_id": envelope.event_id, "event_hash": envelope.event_hash,
                  "envelope": asdict(envelope), "payload": deepcopy(payload)}
    delta = Delta(envelope.event_id, events={envelope.event_id: dependency})
    if claim is not None:
        delta, belief_trees = committed.reduce_claims(snapshot, envelope, [claim], as_of, "3", delta)
        trees = belief_trees[belief_id]
    else:
        _entity_refs(envelope, [belief["subject_id"]])
        trees = snapshot.collection_trees(belief_id)
        trees["event_dependencies"] = merkle.put(trees["event_dependencies"], envelope.event_id,
                                                 dependency, delta.nodes)
        delta.beliefs[belief_id] = {**belief, "updated_at": envelope.recorded_at,
                                   "projected_as_of": as_of}
    status, relation = TRANSITIONS[envelope.event_type]
    for candidate in candidates:
        candidate.update(live_status=status, superseding_events=[envelope.event_id])
        cid = candidate["claim_candidate_id"]
        delta.claim_candidates[cid] = candidate
        delta.relations[cid] = {"target_candidate_id": cid, "event_id": envelope.event_id,
                               "relation": relation, "log_position": snapshot.log_position + 1}
        trees["claim_candidates"] = merkle.put(trees["claim_candidates"], cid, candidate, delta.nodes)
    header = delta.beliefs[belief_id]
    header["collection_roots"] = {k: merkle.digest(v) for k, v in trees.items()}
    header["result_root"] = committed.result_root(header["collection_roots"])
    predecessors = [{"belief_id": belief_id, "view_version_hash": belief["view_version_hash"]}]
    header["view_version_hash"] = hashing._sha256_hex(hashing.canonical_json(
        committed.lineage_for(envelope.event_id, envelope.event_hash, predecessors, header, "3")))
    return committed._finish(snapshot, delta, {belief_id: trees})


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
