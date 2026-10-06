"""B01: interleaved multi-target chain retries, ADR 0034 §§4/8/9."""
from contextlib import closing

from nyx import storage
from queue13_helpers import assert_prefix, contents, request
from test_forward_correction import append, initial_log
from test_reducer_boundary import T2


def test_b01_interleaved_chain_retries_preserve_original_pairs_and_all_prefixes(tmp_path):
    path = tmp_path / "chain.db"
    log = initial_log()
    with closing(storage.init_db(path, create=True, clock=lambda: T2)) as conn:
        for index, pair in enumerate(log):
            append(conn, pair)
            assert_prefix(conn, path, log[:index + 1])
        requests = [request("candidate_replaced", ["c-A", "c-B"], "c-D"),
                    request("correction_appended", ["c-C", "c-D"], "c-E"),
                    request("candidate_expired", ["c-E"], "expiry-E")]
        committed_pairs = []
        for submission in requests:
            pair = storage.append_submission(conn, submission, "3")
            storage.materialize_pending(conn, T2, "3")
            log.append(pair)
            committed_pairs.append(pair)
            assert_prefix(conn, path, log)
            for saved, expected in zip(requests, committed_pairs):
                before = contents(conn)
                assert storage.append_submission(conn, saved, "3") == expected
                assert contents(conn) == before
                assert_prefix(conn, path, log)
        relations = storage.read_snapshot(conn, "3").relations()
        assert {cid: value["relation"] for cid, value in relations.items()} == {
            "c-A": "replaced_by", "c-B": "replaced_by", "c-C": "corrected_by",
            "c-D": "corrected_by", "c-E": "expired_at"}
        assert storage.read_candidate_sets(conn, "b-a", "3")["live"] == []
