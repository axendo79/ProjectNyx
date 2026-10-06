"""B12: coordinated rehashed derived forgery, ADR 0034 §8 independent audit."""
from contextlib import closing
from nyx import committed, committed_storage, hashing, merkle, storage
from queue13_helpers import payload
from test_forward_correction import append
from test_reducer_boundary import claim, event, mention
from test_verify_store import verifier


def test_b12_swapped_endings_with_consistent_commitments_fail_audit(tmp_path):
    path = tmp_path / "forged.db"
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("A"), claim("B")]}, 2, log[-1]))
    log.append(event("candidate_replaced", payload("candidate_replaced", ["A"], "A2"), 3, log[-1]))
    log.append(event("candidate_replaced", payload("candidate_replaced", ["B"], "B2"), 4, log[-1]))
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log[:3]:
            append(conn, pair)
        prior = storage.read_snapshot(conn, "3").header("b-a")["view_version_hash"]
        append(conn, log[3])
        layer_a = storage.read_all_events(conn)
        snapshot = storage.read_snapshot(conn, "3")
        trees = snapshot.collection_trees("b-a")
        global_candidates = snapshot.roots["claim_candidates"]
        nodes = {}
        for cid, ending in [("A", "e-4"), ("B", "e-3")]:
            candidate = snapshot.record("claim_candidates", cid)
            candidate["superseding_events"] = [ending]
            trees["claim_candidates"] = merkle.put(trees["claim_candidates"], cid, candidate, nodes)
            global_candidates = merkle.put(global_candidates, cid, candidate, nodes)
        header = snapshot.header("b-a")
        header["collection_roots"] = {k: merkle.digest(v) for k, v in trees.items()}
        header["result_root"] = committed.result_root(header["collection_roots"])
        header["view_version_hash"] = hashing._sha256_hex(hashing.canonical_json(committed.lineage_for(
            "e-4", log[3][0].event_hash, [{"belief_id": "b-a", "view_version_hash": prior}], header, "3")))
        beliefs = merkle.put(snapshot.roots["beliefs"], "b-a", header, nodes, links=trees)
        delta = committed.Delta("e-4", beliefs={"b-a": header}, nodes=nodes,
                                root_changes={"beliefs": beliefs, "claim_candidates": global_candidates})
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            committed_storage.publish_for(conn, delta, "3")
            conn.execute("UPDATE candidate_relations SET event_id='e-4',log_position=4 WHERE target_candidate_id='A'")
            conn.execute("UPDATE candidate_relations SET event_id='e-3',log_position=3 WHERE target_candidate_id='B'")
        forged = storage.read_snapshot(conn, "3")
        assert committed.full_result_roots(forged.belief("b-a")) == header["collection_roots"]
        assert forged.record("claim_candidates", "A")["superseding_events"] == ["e-4"]
        assert storage.read_all_events(conn) == layer_a
        report = verifier["verify_store"](path, "3")
        assert not report["ok"], report
        assert any(failure["check"] == "relations" for failure in report["failures"]), report
        assert not any(failure["check"] == "merkle" for failure in report["failures"]), report
