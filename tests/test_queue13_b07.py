"""B07: tied instant is inclusive and chain ordered, ADR 0034 §§7,10 / 0010 §1."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import payload
from test_forward_correction import append
from test_forward_replacement import simple_log
from test_reducer_boundary import T2, decoded, event


def tied_log():
    log = simple_log()
    for kind, target, cid, stamp in [
        ("candidate_replaced", "c-a", "replacement", "2026-07-14T00:00:00Z"),
        ("correction_appended", "replacement", "correction", "2026-07-13T20:00:00-04:00"),
        ("candidate_expired", "correction", "unused", "2026-07-14T02:00:00+02:00")]:
        log.append(event(kind, payload(kind, [target], cid), len(log) + 1, log[-1], recorded_at=stamp))
    return log


def test_b07_tied_cutoff_has_complete_chain_in_hash_order(tmp_path):
    log = tied_log()
    before = "2026-07-13T23:59:59.999999Z"
    with closing(storage.init_db(tmp_path / "tied.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        earlier = projection.project_snapshot(decoded(log), before, "3")
        assert earlier.log_position == 2
        assert [c["claim_candidate_id"] for c in earlier.candidate_sets("b-a")["live"]] == ["c-a"]
        assert not earlier.relations()
        exact = projection.project_snapshot(decoded(log), T2, "3")
        assert exact.log_position == 5
        assert exact.candidate_sets("b-a")["live"] == []
        assert [(r["event_id"], r["log_position"]) for r in exact.relations().values()] == [
            ("e-3", 3), ("e-4", 4), ("e-5", 5)]
        assert storage.read_snapshot(conn, "3").complete() == exact.complete()
        storage.rebuild_projection(conn, before, "3")
        assert storage.read_snapshot(conn, "3").complete() == earlier.complete()
        storage.rebuild_projection(conn, T2, "3")
        assert storage.read_snapshot(conn, "3").complete() == exact.complete()
        assert projection.project_snapshot(decoded(log), before, "2").log_position == 2
        with pytest.raises(NotImplementedError, match="candidate_replaced"):
            projection.project_snapshot(decoded(log), T2, "2")
