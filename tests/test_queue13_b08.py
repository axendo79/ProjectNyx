"""B08: compare correction with successor recording event, ADR 0034 §4/R7."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import assert_prefix, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("stamp,allowed", [
    ("2026-07-13T02:00:00+02:00", True),
    ("2026-07-12T23:59:59.999999Z", False)])
def test_b08_correction_compares_successor_not_ancestor(tmp_path, stamp, allowed):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("ancestor")]}, 2, log[-1],
                     occurred_at="2026-07-20T00:00:00Z"))
    log.append(event("candidate_replaced", payload("candidate_replaced", ["ancestor"], "successor"),
                     3, log[-1], occurred_at="2026-07-13T00:00:00Z"))
    correction = event("correction_appended", payload("correction_appended", ["successor"], "fresh"),
                       4, log[-1], occurred_at=stamp)
    path = tmp_path / "successor.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        if allowed:
            append(conn, correction)
            assert_prefix(conn, path, log + [correction])
            assert storage.read_claim_candidate(conn, "successor", "3")["live_status"] == "corrected"
        else:
            before = contents(conn)
            with pytest.raises(projection.BackdatedCorrectionError):
                storage.safe_append_event(conn, *correction, "3")
            assert contents(conn) == before
            with pytest.raises(projection.BackdatedCorrectionError):
                projection.project_snapshot(decoded(log + [correction]), T2, "3")
