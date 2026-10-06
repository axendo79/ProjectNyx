"""B11: pending prefix blocks new eligibility, ADR 0034 §9 / 0014 §9."""
from contextlib import closing
import pytest
from nyx import storage
from queue13_helpers import assert_prefix, contents, request
from test_forward_correction import append
from test_forward_replacement import simple_log
from test_reducer_boundary import T2


def test_b11_pending_replacement_blocks_new_append_but_allows_exact_retry(tmp_path):
    path = tmp_path / "pending.db"
    log = simple_log()
    with closing(storage.init_db(path, create=True, clock=lambda: T2)) as conn:
        for pair in log:
            append(conn, pair)
        replacement = request("candidate_replaced", ["c-a"], "successor")
        committed = storage.append_submission(conn, replacement, "3")
        assert storage.read_snapshot(conn, "3").log_position == 2
        correction = request("correction_appended", ["c-a"], "fresh")
        before = contents(conn)
        with pytest.raises(storage.ProjectionBehindError):
            storage.append_submission(conn, correction, "3")
        assert contents(conn) == before
        assert storage.append_submission(conn, replacement, "3") == committed
        assert contents(conn) == before
        storage.materialize_pending(conn, T2, "3")
        before = contents(conn)
        with pytest.raises(ValueError, match="no longer live"):
            storage.append_submission(conn, correction, "3")
        assert contents(conn) == before
        assert_prefix(conn, path, log + [committed])
