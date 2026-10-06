"""B05: report-marker presence refuses mixed targets, ADR 0035 report refusal."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import canonical_ids, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("kind", ["correction_appended", "candidate_replaced", "candidate_expired"])
@pytest.mark.parametrize("report_id", ["a-report", "z-report"])
@pytest.mark.parametrize("marker", ["v1", ""])
def test_b05_mixed_report_set_refuses_even_empty_marker(tmp_path, kind, report_id, marker):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim("m-ordinary")]}, 2, log[-1],
                     source={"actor_id": "ordinary"}))
    log.append(event("observation_recorded", {"claims": [claim(report_id)]}, 3, log[-1],
                     source={"actor_id": "report", "config": {"report_vocabulary": marker}}))
    targets = canonical_ids(["m-ordinary", report_id])
    assert targets.index(report_id) == (0 if report_id == "a-report" else 1)
    forged = event(kind, payload(kind, targets), 4, log[-1])
    with closing(storage.init_db(tmp_path / "report.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        before = contents(conn)
        with pytest.raises(NotImplementedError, match="report"):
            storage.safe_append_event(conn, *forged, "3")
        assert contents(conn) == before
        with pytest.raises(NotImplementedError, match="report"):
            projection.project_snapshot(decoded(log + [forged]), T2, "3")
