"""B09 / A-G4: latest recording-event occurred_at wins, ADR 0034 §4/R7."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import assert_prefix, canonical_ids, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("late_id", ["a-target", "z-target"])
@pytest.mark.parametrize("stamp,allowed", [
    ("2026-07-13T00:00:01Z", False), ("2026-07-13T00:00:02Z", True)])
def test_b09_every_target_recording_instant_checked(tmp_path, late_id, stamp, allowed):
    early_id = "z-target" if late_id == "a-target" else "a-target"
    log = [event("entity_mention_recorded", mention())]
    for cid, occurred in [(early_id, "2026-07-13T00:00:00Z"),
                           (late_id, "2026-07-13T00:00:02Z")]:
        log.append(event("observation_recorded", {"claims": [claim(cid)]},
                         len(log) + 1, log[-1], occurred_at=occurred))
    correction = event("correction_appended", payload("correction_appended", canonical_ids([early_id, late_id])),
                       4, log[-1], occurred_at=stamp)
    path = tmp_path / "different-instants.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        if allowed:
            append(conn, correction)
            assert_prefix(conn, path, log + [correction])
            assert len(storage.read_candidate_sets(conn, "b-a", "3")["retained"]) == 2
        else:
            before = contents(conn)
            with pytest.raises(projection.BackdatedCorrectionError):
                storage.safe_append_event(conn, *correction, "3")
            assert contents(conn) == before
            with pytest.raises(projection.BackdatedCorrectionError):
                projection.project_snapshot(decoded(log + [correction]), T2, "3")
