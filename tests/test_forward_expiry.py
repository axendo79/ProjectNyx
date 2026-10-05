"""Expiry has no successor and cannot create a scalar winner."""
from contextlib import closing
import json
import pytest
from nyx import events, forward, merkle, projection, storage
from test_forward_correction import append, correction, initial_log
from test_forward_replacement import replacement, simple_log
from test_reducer_boundary import T0, T2, decoded, event


def expiry(targets, bid="b-a"):
    return {"belief_id": bid, "targets": targets,
            "basis": {"kind": "stated", "statement": "no longer live"}}


def test_expiry_no_successor_and_scalar_refusal(tmp_path, monkeypatch):
    from nyx import transition_dependencies
    log = simple_log()
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in log: append(conn, pair)
        calls = []
        original = transition_dependencies.check_transition_dependencies
        def check(snapshot, ids):
            calls.append(tuple(ids))
            original(snapshot, ids)
        monkeypatch.setattr(transition_dependencies, "check_transition_dependencies", check)
        pair = event(events.CANDIDATE_EXPIRED, expiry(["c-a"]), 3, log[-1], occurred_at=T0)
        append(conn, pair)
        snapshot = storage.read_snapshot(conn, "3")
        assert list(snapshot.records("claim_candidates")) == ["c-a"]
        candidate = snapshot.record("claim_candidates", "c-a")
        assert candidate["live_status"] == "expired"
        assert candidate["superseding_events"] == [pair[0].event_id]
        assert not [c for c in snapshot.belief("b-a")["claim_candidates"] if c["live_status"] == "live"]
        with pytest.raises(NotImplementedError): storage.read_belief_scalar(conn, "b-a", "3")
        assert calls == [("c-a",), ("c-a",)]
        assert snapshot.complete() == projection.project_snapshot(decoded(log + [pair]), T2, "3").complete()
        forward.verify_lineage(decoded(log + [pair]), T2)


def test_report_expiry_refuses(tmp_path, monkeypatch):
    log = initial_log({"actor_id": "report", "config": {"report_vocabulary": "v1"}})
    snapshot = projection.project_snapshot(decoded(log), T2, "3")
    pair = event(events.CANDIDATE_EXPIRED, expiry(["c-A"]), 3, log[-1])
    with pytest.raises(NotImplementedError, match="report"):
        projection.project_snapshot(decoded(log + [pair]), T2, "3")
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        ordinary = initial_log()
        for item in ordinary: append(conn, item)
        pair = event(events.CANDIDATE_EXPIRED, expiry(["c-A"]), 3, ordinary[-1])
        monkeypatch.setattr(storage, "_read_snapshot", lambda *args: snapshot)
        before = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match="report"):
            storage.safe_append_event(conn, *pair, "3")
        assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("kind,data", [(events.CORRECTION_APPENDED, correction(["c-A"])),
    (events.CANDIDATE_REPLACED, replacement(["c-A"])), (events.CANDIDATE_EXPIRED, expiry(["c-A"]))])
@pytest.mark.parametrize("damage", ["basis", "predecessors", "restrictions", "opposing_events",
                                     "reverse_predecessors", "reverse_restrictions"])
def test_every_transition_checks_dependencies(tmp_path, monkeypatch, kind, data, damage):
    log = initial_log()
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in log: append(conn, pair)
        snapshot = storage.read_snapshot(conn, "3")
        cid = "c-B" if damage.startswith("reverse_") else "c-A"
        candidate = snapshot.record("claim_candidates", cid)
        if damage == "basis": candidate["verification_basis"]["kind"] = "dependent"
        elif damage.startswith("reverse_"): candidate[damage.removeprefix("reverse_")] = ["c-A"]
        else: candidate[damage] = ["evidence"]
        roots = dict(snapshot.roots)
        roots["claim_candidates"] = merkle.put(roots["claim_candidates"], cid, candidate)
        supplied = forward.Snapshot(roots, 2, log[-1][0].event_id)
        pair = event(kind, data, 3, log[-1])
        with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
            forward.Projector().reduce(supplied, pair[0], json.loads(pair[1].ciphertext), T2)
        monkeypatch.setattr(storage, "_read_snapshot", lambda *args: supplied)
        before = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
            storage.safe_append_event(conn, *pair, "3")
        assert tuple(conn.iterdump()) == before


def canonical_order_log(*, canonical):
    # ADR 0014: set order is canonical JSON UTF-8 bytes. "\n" serializes as
    # backslash-n, so canonical order is ["A", "\n"]; raw string order reverses it.
    from nyx import events, hashing
    from test_reducer_boundary import claim, mention
    first = event(events.ENTITY_MENTION_RECORDED, mention())
    second = event(events.OBSERVATION_RECORDED,
                   {"claims": [claim("A", value="1"), claim("\n", value="2")]}, 2, first)
    targets = hashing.canonical_set(["A", "\n"])
    assert targets == ["A", "\n"] and sorted(targets) == ["\n", "A"]
    if not canonical:
        targets = sorted(targets)
    return [first, second, event(events.CANDIDATE_EXPIRED, expiry(targets), 3, second)]


def test_expiry_targets_use_canonical_set_order():
    accepted = projection.project_snapshot(decoded(canonical_order_log(canonical=True)), T2, "3")
    assert {accepted.record("claim_candidates", cid)["live_status"] for cid in ("A", "\n")} == {"expired"}
    with pytest.raises(ValueError, match="canonical"):
        projection.project_snapshot(decoded(canonical_order_log(canonical=False)), T2, "3")
