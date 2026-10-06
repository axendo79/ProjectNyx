"""Disposable projector-3 fixtures for queue 13; no real store paths."""
from contextlib import closing
from dataclasses import asdict
import json

from nyx import committed, forward, projection, storage, writer
from test_forward_correction import append, initial_log
from test_reducer_boundary import T1, T2, claim, decoded
from test_verify_store import verifier


def canonical_ids(ids):
    """Independent ADR 0014 §6 ordering by canonical UTF-8 JSON bytes."""
    return sorted(set(ids), key=lambda value: json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def payload(kind, targets, cid="fresh", bid="b-a", subject="s-a", prop="RAM", mid="m-a"):
    result = {"targets": list(targets), "basis": {
        "kind": "stated_error" if kind == "correction_appended" else "stated",
        "statement": "synthetic transition reason"}}
    if kind == "candidate_expired":
        result["belief_id"] = bid
    else:
        result["claim"] = claim(cid, bid, subject, mid, prop, value="new")
    return result


def request(kind, targets, cid="fresh", occurred_at=T1, **scope):
    return writer.prepare_event(event_type=kind, origin_type="observed",
        source={"actor_id": "queue13", "config": {}}, source_class="synthetic",
        occurred_at=occurred_at, payload=payload(kind, targets, cid, **scope),
        event_id="request-" + kind + "-" + cid,
        entity_refs=[scope.get("subject", "s-a")])


def assert_prefix(conn, path, log):
    snapshot = storage.read_snapshot(conn, "3")
    replay = projection.project_snapshot(decoded(log), T2, "3")
    assert snapshot.complete() == replay.complete()
    assert (snapshot.log_position, snapshot.event_id) == (len(log), log[-1][0].event_id)
    assert snapshot.relations() == replay.relations()
    rows = conn.execute("SELECT target_candidate_id,event_id,relation,log_position FROM candidate_relations WHERE projector_version='3'").fetchall()
    assert sorted(rows) == sorted((cid, relation["event_id"], relation["relation"], relation["log_position"])
                                 for cid, relation in replay.relations().items())
    for bid, belief in snapshot.beliefs().items():
        roots = committed.full_result_roots(belief)
        assert roots == snapshot.header(bid)["collection_roots"]
        assert committed.result_root(roots) == snapshot.header(bid)["result_root"]
        assert storage.read_candidate_sets(conn, bid, "3") == replay.candidate_sets(bid)
    forward.verify_lineage(decoded(log), T2)
    result = verifier["verify_store"](path, "3")
    assert result["ok"], result


def contents(conn):
    """Complete SQL logical dump, including Layer A, payloads and derived rows."""
    return tuple(conn.iterdump())
