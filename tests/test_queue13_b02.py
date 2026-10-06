"""B02: partly retained target sets refuse atomically, ADR 0034 §4/R6."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import canonical_ids, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("kind", ["correction_appended", "candidate_replaced", "candidate_expired"])
@pytest.mark.parametrize("stale", ["a-stale", "z-stale"])
def test_b02_partly_stale_set_refuses_before_append_and_at_replay(tmp_path, kind, stale):
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim(stale), claim("m-live")]}, 2, log[-1]))
    log.append(event("candidate_replaced", payload("candidate_replaced", [stale], "replacement"), 3, log[-1]))
    targets = canonical_ids([stale, "m-live"])
    assert targets.index(stale) == (0 if stale == "a-stale" else 1)
    forged = event(kind, payload(kind, targets), 4, log[-1])
    with closing(storage.init_db(tmp_path / "stale.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        before = contents(conn)
        with pytest.raises(ValueError, match="no longer live"):
            storage.safe_append_event(conn, *forged, "3")
        assert contents(conn) == before
        with pytest.raises(ValueError, match="no longer live"):
            projection.project_snapshot(decoded(log + [forged]), T2, "3")
