"""Evidence-only helpers. No production module, schema or wire bytes are edited."""
from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from nyx import forward, merkle, transition_dependencies

ROOT = Path(__file__).resolve().parents[1]
EXPRESSION = "roots = {k: merkle.digest(merkle.rebuild(v.items())) for k, v in self.collections[bid].items()}"


class Members(dict):
    """Remember writes to verifier-owned logical members; never load stored roots."""
    def __init__(self):
        super().__init__()
        self.tree = None
        self.dirty = set()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.dirty.add(key)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.dirty.add(key)

    def root(self):
        # Delay hashing until the original root-computation point, preserving
        # the original replay's validation/exception ordering.
        for key in sorted(self.dirty):
            self.tree = (merkle.put(self.tree, key, self[key]) if key in self
                         else merkle.delete(self.tree, key))
        self.dirty.clear()
        return merkle.digest(self.tree)


class Collections(dict):
    def setdefault(self, bid, default):
        if bid not in self:
            super().__setitem__(bid, {name: Members() for name in default})
        return self[bid]


def replay_roots(replay, bid):
    return {name: members.root() for name, members in replay.collections[bid].items()}


def verifier(prototype=False):
    """Compile the shipped verifier with exactly one expression substituted.

    Its SQL/log reader, semantic replay, stored-node audit, lineage checks and
    reports remain the same source. This explicit seam avoids installing an
    experimental default in scripts/verify_store.py.
    """
    path = ROOT / "scripts" / "verify_store.py"
    source = path.read_text(encoding="utf-8")
    module = ModuleType("verify_store")
    module.__file__ = str(path)
    if prototype:
        assert source.count(EXPRESSION) == 1, "verifier seam changed"
        source = source.replace(EXPRESSION, "roots = replay_roots(self, bid)")
        module.replay_roots = replay_roots
    exec(compile(source, str(path), "exec"), module.__dict__)
    if prototype:
        original = module.Replay
        class IncrementalReplay(original):
            def __init__(self, version, conn):
                super().__init__(version, conn)
                self.collections = Collections()
        module.Replay = IncrementalReplay
    return module


class ReverseIndex:
    """Experimental in-memory predicate index, owned by one replay trajectory.

    A target -> set(candidate IDs) reverse map is updated only from complete
    event deltas. It is never cached against a database digest or loaded from
    materialized storage. Unsupported field shapes fall back to the scanner.
    """
    def __init__(self):
        self.by_target = defaultdict(set)
        self.refs = {}
        self.fallback = {}

    def update(self, identifier, candidate):
        for target in self.refs.pop(identifier, ()):
            self.by_target[target].discard(identifier)
            if not self.by_target[target]:
                del self.by_target[target]
        self.fallback.pop(identifier, None)
        fields = [candidate[k] for k in ("predecessors", "restrictions")]
        if not all(isinstance(value, list) for value in fields):
            self.fallback[identifier] = deepcopy(candidate)
            return
        refs = {ref for value in fields for ref in value if isinstance(ref, str)}
        if refs:
            self.refs[identifier] = refs
        for target in refs:
            self.by_target[target].add(identifier)

    def fork(self):
        result = type(self)()
        result.by_target = defaultdict(set, {k: set(v) for k, v in self.by_target.items()})
        result.refs = {k: set(v) for k, v in self.refs.items()}
        result.fallback = deepcopy(self.fallback)
        return result

    def check(self, snapshot, targets):
        for identifier in targets:
            candidate = snapshot.record("claim_candidates", identifier)
            if candidate is None:
                # The real handler checks existence before calling R9.
                raise ValueError("missing target")
            if (candidate["verification_basis"]["kind"] != "direct_observation"
                    or candidate["predecessors"] or candidate["restrictions"]
                    or candidate["opposing_events"]):
                raise NotImplementedError("transition dependency requires ADR 0015 section 5")
        if any(self.by_target.get(identifier) for identifier in targets):
            raise NotImplementedError("transition dependency requires ADR 0015 section 5")
        for candidate in self.fallback.values():
            if any(identifier in candidate[k] for identifier in targets
                   for k in ("predecessors", "restrictions")):
                raise NotImplementedError("transition dependency requires ADR 0015 section 5")


@dataclass(frozen=True)
class IndexedSnapshot(forward.Snapshot):
    dependency_index: object = field(default_factory=ReverseIndex, compare=False)

    def apply(self, delta, position):
        # Fork the sparse edge map so previous immutable snapshots remain valid.
        # Ordinary stage-two candidates add no edges, so this copies empty maps.
        # No database/detached snapshot is assigned an unproven cached index.
        dependency_index = self.dependency_index.fork()
        for identifier, candidate in delta.claim_candidates.items():
            dependency_index.update(identifier, candidate)
        return type(self)(delta.roots, position, delta.event_id, dependency_index)


@contextmanager
def indexed_dependencies():
    original = transition_dependencies.check_transition_dependencies
    def check(snapshot, targets):
        if isinstance(snapshot, IndexedSnapshot):
            return snapshot.dependency_index.check(snapshot, targets)
        return original(snapshot, targets)
    transition_dependencies.check_transition_dependencies = check
    try:
        yield
    finally:
        transition_dependencies.check_transition_dependencies = original
