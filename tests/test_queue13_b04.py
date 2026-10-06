"""B04 / A-G3: real foreign scopes refuse atomically, ADR 0034 §4/R5."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import canonical_ids, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("kind", ["correction_appended", "candidate_replaced", "candidate_expired"])
@pytest.mark.parametrize("foreign", ["other-property", "other-subject"])
def test_b04_real_foreign_target_refuses_whole_event(tmp_path, kind, foreign):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("entity_mention_recorded", mention("s-b", "m-b"), 2, log[-1]))
    claims = [claim("same", value="equal"),
              claim("other-property", "b-q", prop="Q", value="equal"),
              claim("other-subject", "b-b", "s-b", "m-b", value="equal")]
    log.append(event("observation_recorded", {"claims": claims}, 3, log[-1]))
    forged = event(kind, payload(kind, canonical_ids(["same", foreign])), 4, log[-1])
    with closing(storage.init_db(tmp_path / "foreign.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        assert set(storage.read_snapshot(conn, "3").beliefs()) == {"b-a", "b-q", "b-b"}
        before = contents(conn)
        with pytest.raises(ValueError, match="scope"):
            storage.safe_append_event(conn, *forged, "3")
        assert contents(conn) == before
        with pytest.raises(ValueError, match="scope"):
            projection.project_snapshot(decoded(log + [forged]), T2, "3")
