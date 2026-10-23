"""Bounded prefix and dependency equivalence evidence."""
from contextlib import closing
from dataclasses import asdict
from copy import deepcopy
import sys

import pytest

from deephist_prototype import ROOT, ReverseIndex, verifier
sys.path.insert(0, str(ROOT / "scripts"))
import replay_campaign
from nyx import ingestion, storage, reducer, transition_dependencies


@pytest.mark.parametrize("version", ["0", "1", "2", "3"])
@pytest.mark.parametrize("seed", [0, 17, 902467])
def test_every_full_verifier_prefix(tmp_path, version, seed):
    old, new = verifier(), verifier(True)
    path = tmp_path / "prefix.sqlite"
    a, b = old.Replay(version, None), new.Replay(version, None)
    with closing(storage.init_db(path, create=True)) as conn:
        a.conn = b.conn = conn
        assert old.verify_store(path, version) == new.verify_store(path, version)
        for step in replay_campaign.generate(version, seed, 24):
            conn.clock = lambda: step["recorded_at"]
            pair = replay_campaign.prepare(conn, step, version)
            committed = ingestion.submit(conn, pair, replay_campaign.AS_OF, version)
            envelope, payload = asdict(committed[0]), step["data"]
            a.append(envelope, payload)
            b.append(envelope, payload)
            assert a.records == b.records
            assert a.history == b.history
            before = path.read_bytes()
            assert old.verify_store(path, version) == new.verify_store(path, version)
            assert path.read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("verification_basis", {"kind": "approval"}),
    ("predecessors", ["other"]), ("restrictions", ["other"]),
    ("opposing_events", ["other"]), ("superseding_events", ["ending"]),
    ("predecessors", []),
])
def test_index_target_predicate(field, value):
    target = dict(verification_basis={"kind": "direct_observation"},
                  predecessors=[], restrictions=[], opposing_events=[])
    target[field] = value
    compare({"target": target}, ["target"])


@pytest.mark.parametrize("field", ["predecessors", "restrictions"])
@pytest.mark.parametrize("value", [["target"], ["unrelated"], "target", {"target": 1}])
def test_index_reverse_predicate_and_removal(field, value):
    target = dict(verification_basis={"kind": "direct_observation"},
                  predecessors=[], restrictions=[], opposing_events=[])
    other = deepcopy(target)
    other[field] = value
    index = compare({"target": target, "other": other}, ["target"])
    # Replacement/removal must not leave a stale negative/positive entry.
    previous = index.fork()
    index.update("other", target)
    assert previous.refs != index.refs or previous.fallback != index.fallback or value == ["unrelated"]
    view = reducer.Snapshot({}, claim_candidates={"target": target, "other": target}, projector_version="3")
    index.check(view, ["target"])
    transition_dependencies.check_transition_dependencies(view, ["target"])


def compare(records, targets):
    index = ReverseIndex()
    for cid, candidate in records.items():
        index.update(cid, candidate)
    view = reducer.Snapshot({}, claim_candidates=records, projector_version="3")
    def outcome(call):
        try:
            call()
        except (NotImplementedError, ValueError, TypeError, KeyError) as error:
            return type(error).__name__, str(error)
        return "pass"
    assert outcome(lambda: index.check(view, targets)) == outcome(
        lambda: transition_dependencies.check_transition_dependencies(view, targets))
    return index
