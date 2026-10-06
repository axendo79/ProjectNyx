"""A-G8: mixed-standing one-target correction, ADR 0034 §4/R9 acceptance A1."""
import json
from nyx import committed, forward, merkle, projection
from queue13_helpers import payload
from test_forward_correction import initial_log
from test_reducer_boundary import T2, decoded, event


def test_ag8_one_target_mixed_standing_preserves_untargeted_candidates():
    log = initial_log()
    original = projection.project_snapshot(decoded(log), T2, "3")
    roots = dict(original.roots)
    trees = original.collection_trees("b-a")
    # Supplied standing fixture, as in existing mixed-standing coverage. This
    # does not invent producers for undecided verification-state transitions.
    for cid, state in [("c-B", "questioned"), ("c-C", "unverified")]:
        candidate = original.record("claim_candidates", cid)
        candidate["verification_state"] = state
        roots["claim_candidates"] = merkle.put(roots["claim_candidates"], cid, candidate)
        trees["claim_candidates"] = merkle.put(trees["claim_candidates"], cid, candidate)
    header = original.header("b-a")
    header["collection_roots"] = {k: merkle.digest(v) for k, v in trees.items()}
    header["result_root"] = committed.result_root(header["collection_roots"])
    roots["beliefs"] = merkle.put(roots["beliefs"], "b-a", header, links=trees)
    supplied = forward.Snapshot(roots, original.log_position, original.event_id)
    before = supplied.records("claim_candidates")
    assert [(before[c]["value"], before[c]["verification_state"]) for c in ("c-A", "c-B", "c-C")] == [
        ("64", "verified"), ("64", "questioned"), ("128", "unverified")]
    pair = event("correction_appended", payload("correction_appended", ["c-A"], "fresh"), 3, log[-1])
    delta = forward.Projector().reduce(supplied, pair[0], json.loads(pair[1].ciphertext), T2)
    after = supplied.apply(delta, 3)
    for cid in ("c-B", "c-C"):
        assert after.record("claim_candidates", cid) == before[cid]
    assert after.record("claim_candidates", "c-A") == {
        **before["c-A"], "live_status": "corrected", "superseding_events": ["e-3"]}
    fresh = after.record("claim_candidates", "fresh")
    assert fresh["verification_state"] == "verified"
    assert fresh["verification_basis"] == {"kind": "direct_observation", "event_ids": ["e-3"]}
    assert fresh["supporting_events"] == ["e-3"] and fresh["opposing_events"] == []
    assert {c["claim_candidate_id"] for c in after.candidate_sets("b-a")["live"]} == {"c-B", "c-C", "fresh"}
    assert list(after.relations()) == ["c-A"]
    assert committed.full_result_roots(after.belief("b-a")) == after.header("b-a")["collection_roots"]
