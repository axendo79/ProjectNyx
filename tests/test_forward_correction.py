"""Ordinary corrections at the locked append prefix and the same replay seam."""
from contextlib import closing
import json

import pytest

from nyx import events, forward, ingestion, merkle, projection, storage, writer
from test_reducer_boundary import T0, T1, T2, claim, decoded, event, mention


def initial_log(source=None):
    first = event(events.ENTITY_MENTION_RECORDED, mention())
    changes = {} if source is None else {"source": source}
    second = event(events.OBSERVATION_RECORDED, {"claims": [
        claim("c-A", value="64"), claim("c-B", value="64"), claim("c-C", value="128")]},
        2, first, **changes)
    return [first, second]


def correction(targets, cid="c-new"):
    return {"claim": claim(cid, value="32"), "targets": targets,
            "basis": {"kind": "stated_error", "statement": "record was wrong"}}


def append(conn, pair):
    storage.safe_append_event(conn, *pair, "3")
    storage.materialize_pending(conn, T2, "3")


@pytest.fixture
def store(tmp_path):
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        log = initial_log()
        for pair in log:
            append(conn, pair)
        yield conn, log


@pytest.mark.parametrize("targets", [["c-A"], ["c-A", "c-B", "c-C"]])
def test_one_and_all_targets(store, targets, monkeypatch):
    from nyx import transition_dependencies
    conn, log = store
    before = storage.read_snapshot(conn, "3")
    calls = []
    original = transition_dependencies.check_transition_dependencies
    def check(snapshot, ids):
        calls.append(tuple(ids))
        return original(snapshot, ids)
    monkeypatch.setattr(transition_dependencies, "check_transition_dependencies", check)
    pair = event(events.CORRECTION_APPENDED, correction(targets), 3, log[-1])
    append(conn, pair)
    after = storage.read_snapshot(conn, "3")
    assert calls and all(call == tuple(targets) for call in calls)
    for cid in ("c-A", "c-B", "c-C"):
        candidate = after.record("claim_candidates", cid)
        expected = before.record("claim_candidates", cid)
        if cid in targets:
            expected.update(live_status="corrected", superseding_events=[pair[0].event_id])
        assert candidate == expected
    assert after.record("claim_candidates", "c-new")["verification_basis"] == {
        "kind": "direct_observation", "event_ids": [pair[0].event_id]}
    assert after.complete() == projection.project_snapshot(decoded(log + [pair]), T2, "3").complete()
    forward.verify_lineage(decoded(log + [pair]), T2)


@pytest.mark.parametrize("damage", ["empty", "duplicate", "foreign", "unknown", "fresh_target",
                                    "wrong_subject", "basis", "extra", "unsorted"])
def test_invalid_before_append_and_forged_replay(store, damage):
    conn, log = store
    data = correction(["c-A"])
    if damage == "empty": data["targets"] = []
    if damage == "duplicate": data["targets"] = ["c-A", "c-A"]
    if damage == "unknown": data["targets"] = ["c-A", "missing"]
    if damage == "foreign": data["claim"]["belief_id"] = "other"
    if damage == "fresh_target": data["claim"]["claim_candidate_id"] = "c-A"
    if damage == "wrong_subject": data["claim"]["subject_id"] = "other"
    if damage == "basis": data["basis"]["kind"] = "stated"
    if damage == "extra": data["extra"] = "not allowed"
    if damage == "unsorted": data["targets"] = ["c-C", "c-A"]
    pair = event(events.CORRECTION_APPENDED, data, 3, log[-1])
    before = tuple(conn.iterdump())
    with pytest.raises(ValueError):
        storage.safe_append_event(conn, *pair, "3")
    assert tuple(conn.iterdump()) == before
    with pytest.raises(ValueError):
        projection.project_snapshot(decoded(log + [pair]), T2, "3")


@pytest.mark.parametrize("stamp,allowed", [(T0, False), (T1, True),
    ("2026-07-12T20:00:00-04:00", True), ("2026-07-12T19:59:59-04:00", False)])
def test_timestamp_instants(store, stamp, allowed):
    conn, log = store
    pair = event(events.CORRECTION_APPENDED, correction(["c-A"]), 3, log[-1], occurred_at=stamp)
    if allowed:
        append(conn, pair)
    else:
        before = tuple(conn.iterdump())
        with pytest.raises(projection.BackdatedCorrectionError):
            storage.safe_append_event(conn, *pair, "3")
        with pytest.raises(projection.BackdatedCorrectionError):
            projection.project_snapshot(decoded(log + [pair]), T2, "3")
        assert tuple(conn.iterdump()) == before


def test_fresh_candidate_can_be_corrected_and_stale_target_refuses(store):
    conn, log = store
    first = event(events.CORRECTION_APPENDED, correction(["c-A"]), 3, log[-1])
    append(conn, first)
    stale = event(events.CORRECTION_APPENDED, correction(["c-A"], "c-other"), 4, first)
    before = tuple(conn.iterdump())
    with pytest.raises(ValueError, match="live"):
        storage.safe_append_event(conn, *stale, "3")
    assert tuple(conn.iterdump()) == before
    second = event(events.CORRECTION_APPENDED, correction(["c-new"], "c-next"), 4, first)
    append(conn, second)
    assert storage.read_claim_candidate(conn, "c-new", "3")["live_status"] == "corrected"


def test_report_target_refuses_append_and_replay(store):
    # Report ingestion stays on 2; replay the recorded ordinary contract on 3.
    conn, log = store
    snapshot = storage.read_snapshot(conn, "3")
    candidate = snapshot.record("claim_candidates", "c-A")
    candidate["source"]["config"]["report_vocabulary"] = "recorded-report"
    roots = dict(snapshot.roots)
    roots["claim_candidates"] = merkle.put(roots["claim_candidates"], "c-A", candidate)
    scoped = forward.Snapshot(roots, snapshot.log_position, snapshot.event_id)
    pair = event(events.CORRECTION_APPENDED, correction(["c-A"]), 3, log[-1])
    with pytest.raises(NotImplementedError, match="report"):
        forward.Projector().reduce(scoped, pair[0], json.loads(pair[1].ciphertext), T2)
    # Feed the same recorded snapshot at the locked append seam.
    from unittest.mock import patch
    before = tuple(conn.iterdump())
    with patch.object(storage, "_read_snapshot", return_value=scoped):
        with pytest.raises(NotImplementedError, match="report"):
            storage.safe_append_event(conn, *pair, "3")
    assert tuple(conn.iterdump()) == before
    recorded = initial_log({"actor_id": "report", "config": {"report_vocabulary": "v1"}})
    forged = event(events.CORRECTION_APPENDED, correction(["c-A"]), 3, recorded[-1])
    with pytest.raises(NotImplementedError, match="report"):
        projection.project_snapshot(decoded(recorded + [forged]), T2, "3")


def test_sole_writer_correction_and_retry(store):
    conn, log = store
    conn.clock = lambda: T2
    request = writer.prepare_event(event_type=events.CORRECTION_APPENDED, origin_type="observed",
        source={"actor_id": "different-operator", "config": {}}, source_class="direct_observation",
        occurred_at=T1, payload=correction(["c-A"]), entity_refs=["s-a"], event_id="ordinary-correction")
    result = ingestion.submit(conn, request, T2, "3")
    assert ingestion.submit(conn, request, T2, "3") == result
    assert conn.execute("SELECT count(*) FROM events").fetchone() == (3,)


def test_different_standing_is_retained(store):
    conn, log = store
    snapshot = storage.read_snapshot(conn, "3")
    candidate = snapshot.record("claim_candidates", "c-B")
    candidate["verification_state"] = "questioned"
    roots = dict(snapshot.roots)
    roots["claim_candidates"] = merkle.put(roots["claim_candidates"], "c-B", candidate)
    trees = snapshot.collection_trees("b-a")
    trees["claim_candidates"] = merkle.put(trees["claim_candidates"], "c-B", candidate)
    header = snapshot.header("b-a")
    header["collection_roots"] = {k: merkle.digest(v) for k, v in trees.items()}
    header["result_root"] = forward.committed.result_root(header["collection_roots"])
    roots["beliefs"] = merkle.put(roots["beliefs"], "b-a", header, links=trees)
    supplied = forward.Snapshot(roots, 2, log[-1][0].event_id)
    pair = event(events.CORRECTION_APPENDED, correction(["c-A", "c-B", "c-C"]), 3, log[-1])
    delta = forward.Projector().reduce(supplied, pair[0], json.loads(pair[1].ciphertext), T2)
    after = supplied.apply(delta, 3)
    assert after.record("claim_candidates", "c-B")["verification_state"] == "questioned"
    assert after.record("claim_candidates", "c-new")["verification_state"] == "verified"
