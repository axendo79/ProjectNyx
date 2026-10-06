"""B06: untargeted reports survive ordinary chains, ADR 0034 §4 / 0035 §3."""
from contextlib import closing
from nyx import storage
from queue13_helpers import assert_prefix, payload
from test_forward_correction import append
from test_reducer_boundary import claim, event, mention


def test_b06_untargeted_report_unchanged_through_ordinary_chain(tmp_path):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("ordinary")]}, 2, log[-1],
                     source={"actor_id": "ordinary"}))
    log.append(event("observation_recorded", {"claims": [claim("report")]}, 3, log[-1],
                     source={"actor_id": "report", "config": {"report_vocabulary": "v1"}}))
    path = tmp_path / "coexisting.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
            assert_prefix(conn, path, log[:conn.execute("SELECT count(*) FROM events").fetchone()[0]])
        report = storage.read_claim_candidate(conn, "report", "3")
        for kind, target, fresh in [("candidate_replaced", "ordinary", "replacement"),
                                    ("correction_appended", "replacement", "correction"),
                                    ("candidate_expired", "correction", "unused")]:
            pair = event(kind, payload(kind, [target], fresh), len(log) + 1, log[-1],
                         source={"actor_id": "ordinary"})
            append(conn, pair)
            log.append(pair)
            assert storage.read_claim_candidate(conn, "report", "3") == report
            assert_prefix(conn, path, log)
        sets = storage.read_candidate_sets(conn, "b-a", "3")
        assert [c["claim_candidate_id"] for c in sets["live"]] == ["report"]
        assert {r["candidate"]["claim_candidate_id"] for r in sets["retained"]} == {
            "ordinary", "replacement", "correction"}
