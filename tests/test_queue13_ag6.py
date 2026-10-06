"""A-G6: correction successor supports replacement and expiry, ADR 0035 acceptance B4."""
from contextlib import closing
import pytest
from nyx import storage
from queue13_helpers import assert_prefix, payload
from test_forward_correction import append
from test_forward_replacement import simple_log
from test_reducer_boundary import event


@pytest.mark.parametrize("kind,status,relation", [
    ("candidate_replaced", "replaced", "replaced_by"),
    ("candidate_expired", "expired", "expired_at")])
def test_ag6_fresh_correction_candidate_can_be_replaced_or_expired(tmp_path, kind, status, relation):
    path = tmp_path / "correction-successor.db"
    log = simple_log()
    log.append(event("correction_appended", payload("correction_appended", ["c-a"], "correction"), 3, log[-1]))
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        correction = storage.read_claim_candidate(conn, "correction", "3")
        assert correction["live_status"] == "live"
        assert correction["verification_basis"] == {"kind": "direct_observation", "event_ids": ["e-3"]}
        assert correction["verification_state"] == "verified" and correction["supporting_events"] == ["e-3"]
        pair = event(kind, payload(kind, ["correction"], "replacement"), 4, log[-1])
        append(conn, pair)
        log.append(pair)
        assert_prefix(conn, path, log)
        details = storage.read_claim_candidate_details(conn, "correction", "3")
        assert details["candidate"] == {**correction, "live_status": status, "superseding_events": ["e-4"]}
        assert details["ending_relation"] == {"target_candidate_id": "correction", "event_id": "e-4",
                                              "relation": relation, "log_position": 4}
        sets = storage.read_candidate_sets(conn, "b-a", "3")
        assert [c["claim_candidate_id"] for c in sets["live"]] == (["replacement"] if kind == "candidate_replaced" else [])
        assert len(sets["retained"]) == 2
        assert len(storage.read_snapshot(conn, "3").records("claim_candidates")) == (3 if kind == "candidate_replaced" else 2)
