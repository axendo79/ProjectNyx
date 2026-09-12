"""Projector 2: complete result coverage with incremental storage (ADR 0025)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from types import MappingProxyType

from . import hashing, merkle
from .events import ENTITY_MENTION_RECORDED
from .reducer import (EventDelta, RECORD_KINDS, SUPPORTED_EVENTS, ReducerProjector,
                      _entity_refs, _fields, _fresh, _required, _string,
                      canonical_claim_candidates, identity_confidence_ceiling)

PROJECTOR_VERSION = "2"
COLLECTIONS = ("claim_candidates", "event_dependencies", "identity_records")
INDEX_KINDS = (*RECORD_KINDS, "current_beliefs")


def pair_key(subject, prop):
    return hashing.canonical_json([subject, prop])


def member_key(kind, member):
    if kind == "claim_candidates":
        return member["claim_candidate_id"]
    if kind == "event_dependencies":
        return member["event_id"]
    if kind == "identity_records":
        return hashing.canonical_json(member)
    raise ValueError(f"unknown committed collection: {kind}")


def result_root(roots):
    return hashing._sha256_hex(hashing.canonical_json(
        {"format": "nyx-result/1", "collections": roots}))


def lineage(event_id, event_hash, predecessors, header):
    return {
        "lineage_format": "nyx-belief-lineage/2", "projector_version": "2",
        "producing_event": {"event_id": event_id, "event_hash": event_hash},
        "predecessors": hashing.canonical_set(predecessors),
        "result": {k: v for k, v in header.items() if k not in (
            *COLLECTIONS, "view_version_hash", "projected_as_of", "collection_roots", "result_root")},
        "collection_roots": header["collection_roots"], "result_root": header["result_root"],
    }


def full_result_roots(belief):
    """Independent full-content rebuild, used for audits and replay acceptance."""
    roots = {}
    for kind in COLLECTIONS:
        members = (canonical_claim_candidates(belief[kind]) if kind == "claim_candidates"
                   else hashing.canonical_set(belief[kind]))
        seen = {}
        for member in members:
            key = member_key(kind, member)
            if key in seen and seen[key] != member:
                raise ValueError("inconsistent committed member identity")
            seen[key] = member
        roots[kind] = merkle.digest(merkle.rebuild(seen.items()))
    return roots


@dataclass(frozen=True)
class Snapshot:
    roots: object = field(default_factory=lambda: MappingProxyType(dict.fromkeys(INDEX_KINDS)))
    log_position: int = 0
    event_id: str | None = None
    projector_version: str = field(default=PROJECTOR_VERSION, init=False)

    def __post_init__(self):
        if set(self.roots) != set(INDEX_KINDS):
            raise ValueError("snapshot requires every version-2 record root")
        object.__setattr__(self, "roots", MappingProxyType(dict(self.roots)))

    def header(self, belief_id):
        return merkle.get(self.roots["beliefs"], belief_id)

    def collection_trees(self, belief_id):
        leaf = merkle.get_leaf(self.roots["beliefs"], belief_id)
        if leaf is None:
            return dict.fromkeys(COLLECTIONS)
        header = json.loads(leaf.value)
        links = dict(leaf.links)
        if (set(links) != set(COLLECTIONS)
                or {k: merkle.digest(v) for k, v in links.items()} != header["collection_roots"]
                or result_root(header["collection_roots"]) != header["result_root"]):
            raise ValueError("belief collection roots do not match committed header")
        return links

    def belief(self, belief_id):
        header = self.header(belief_id)
        if header is None:
            return None
        trees = self.collection_trees(belief_id)
        result = {k: v for k, v in header.items() if k not in ("collection_roots", "result_root")}
        for kind, tree in trees.items():
            result[kind] = hashing.canonical_set([value for _, value in merkle.items(tree)])
        return result

    def record(self, kind, identifier):
        if kind == "beliefs":
            return self.belief(identifier)
        return merkle.get(self.roots[kind], identifier)

    def records(self, kind):
        if kind == "beliefs":
            return self.beliefs()
        return dict(sorted(merkle.items(self.roots[kind])))

    def beliefs(self):
        return {key: self.belief(key) for key, _ in sorted(merkle.items(self.roots["beliefs"]))}

    def complete(self):
        return {kind: self.records(kind) for kind in RECORD_KINDS}

    def event(self, event_id):
        return self.record("events", event_id)

    def events(self):
        return self.records("events")

    def current_belief(self, subject_id, property_id):
        key = merkle.get(self.roots["current_beliefs"], pair_key(subject_id, property_id))
        return None if key is None else self.header(key)

    def apply(self, delta, position):
        return Snapshot(delta.roots, position, delta.event_id)

    def detached(self):
        cache = {}
        return Snapshot({k: merkle.detach(v, cache) for k, v in self.roots.items()},
                        self.log_position, self.event_id)

    def inclusion_proof(self, belief_id, collection, key):
        tree = self.collection_trees(belief_id)[collection]
        return merkle.prove(tree, key)


@dataclass(frozen=True)
class Delta(EventDelta):
    nodes: dict[str, str] = field(default_factory=dict)
    roots: dict = field(default_factory=dict)
    root_changes: dict = field(default_factory=dict)


def _finish(snapshot, delta, belief_trees):
    roots = dict(snapshot.roots)
    for kind in RECORD_KINDS:
        for key, value in sorted(getattr(delta, kind).items()):
            links = belief_trees[key] if kind == "beliefs" else None
            roots[kind] = merkle.put(roots[kind], key, value, delta.nodes, links=links)
            if kind == "beliefs" and value["lifecycle_status"] == "current":
                roots["current_beliefs"] = merkle.put(
                    roots["current_beliefs"], pair_key(value["subject_id"], value["property_id"]),
                    key, delta.nodes)
    delta.roots.update(roots)
    delta.root_changes.update({k: v for k, v in roots.items()
                               if snapshot.log_position == 0
                               or merkle.digest(v) != merkle.digest(snapshot.roots[k])})
    return delta


def reduce(snapshot, envelope, payload, as_of):
    from .projection import _instant, _state_for_origin

    if not isinstance(snapshot, Snapshot) or snapshot.projector_version != PROJECTOR_VERSION:
        raise ValueError("snapshot projector version does not match reducer")
    if envelope.event_type not in SUPPORTED_EVENTS:
        raise NotImplementedError(f"stage two refuses {envelope.event_type!r}")
    _instant(as_of, "as_of")
    _instant(envelope.occurred_at)
    _instant(envelope.recorded_at, "recorded_at")
    _string(asdict(envelope), "event_id")
    source = json.loads(envelope.source)
    _string(source, "actor_id")
    _string(asdict(envelope), "source_class")
    _fresh(snapshot, "events", envelope.event_id, {})
    dependency = {"event_id": envelope.event_id, "event_hash": envelope.event_hash,
                  "envelope": asdict(envelope),
                  "payload": json.loads(hashing.canonical_json(payload))}
    delta = Delta(envelope.event_id, events={envelope.event_id: dependency})
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
            "constituting_mention_id": mention_id, "event_id": envelope.event_id, "predecessors": [],
        }
        delta.mentions[mention_id] = {
            "mention_id": mention_id, "text": payload["text"], "subject_id": subject_id,
            "event_id": envelope.event_id,
        }
        delta.entity_links[mention_id] = {
            "mention_id": mention_id, "subject_id": subject_id,
            "link_state": "constitutive", "entity_link_confidence": None, "event_id": envelope.event_id,
        }
        _entity_refs(envelope, [subject_id])
        return _finish(snapshot, delta, {})

    state = _state_for_origin(envelope.origin_type)
    _fields(payload, ("claims",))
    if not isinstance(payload["claims"], list) or not payload["claims"]:
        raise ValueError("observation requires nonempty explicitly scoped claims")
    belief_trees = {}
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
        if (entity["lifecycle_status"] != "current" or mention["subject_id"] != subject_id
                or link["subject_id"] != subject_id):
            raise ValueError("mention/subject association does not match recorded identity")
        identity_confidence_ceiling([link])
        belief_id, candidate_id = claim["belief_id"], claim["claim_candidate_id"]
        _fresh(snapshot, "claim_candidates", candidate_id, delta.claim_candidates)
        current = snapshot.current_belief(subject_id, claim["property_id"])
        if current is not None and current["belief_id"] != belief_id:
            raise ValueError("subject/property already has a current belief; name its existing ID")
        prior = snapshot.header(belief_id)
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
                      "predecessors": [], "resolution_status": "no_authoritative_head"}
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
        if belief_id not in belief_trees:
            belief_trees[belief_id] = snapshot.collection_trees(belief_id)
        trees = belief_trees[belief_id]
        additions = {
            "claim_candidates": [candidate],
            "identity_records": [{"entity": entity, "mention": mention, "link": link}],
            "event_dependencies": [dependency, _required(snapshot, "events", link["event_id"])],
        }
        for kind, members in additions.items():
            for member in members:
                key = member_key(kind, member)
                existing = merkle.get(trees[kind], key)
                if existing is not None and existing != member:
                    raise ValueError("inconsistent committed member identity")
                trees[kind] = merkle.put(trees[kind], key, member, delta.nodes)
        result = dict(belief)
        result["collection_roots"] = {k: merkle.digest(v) for k, v in trees.items()}
        result["result_root"] = result_root(result["collection_roots"])
        result["projected_as_of"] = as_of
        result["updated_at"] = envelope.recorded_at
        delta.beliefs[belief_id] = result

    _entity_refs(envelope, [b["subject_id"] for b in delta.beliefs.values()])
    for belief_id, result in delta.beliefs.items():
        prior = snapshot.header(belief_id)
        predecessors = [] if prior is None else [{
            "belief_id": belief_id, "view_version_hash": prior["view_version_hash"]}]
        result["view_version_hash"] = hashing._sha256_hex(hashing.canonical_json(
            lineage(envelope.event_id, envelope.event_hash, predecessors, result)))
    return _finish(snapshot, delta, belief_trees)


class Projector(ReducerProjector):
    def reduce(self, snapshot, envelope, payload, as_of):
        return reduce(snapshot, envelope, payload, as_of)
