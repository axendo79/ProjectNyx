"""B16: old-side equivalence mutations refuse, ADR 0034 §1a."""
from copy import deepcopy
from dataclasses import replace
import pytest
from nyx import forward, projection
from test_event_integrity import entries
from test_reducer_boundary import T2, decoded


@pytest.mark.parametrize("field", ["supporting_events", "source.config", "subject_id", "log_position", "event_id"])
def test_b16_old_side_must_equal_mutations_reject(field):
    log = decoded(entries("2"))
    old = projection.project_snapshot(log, T2, "2")
    new = projection.project_snapshot(log, T2, "3")
    forward.assert_semantically_equivalent(old, new)
    if field in ("log_position", "event_id"):
        changed = replace(old, **{field: old.log_position - 1 if field == "log_position" else "wrong-event"})
        with pytest.raises(ValueError, match="progress"):
            forward.assert_semantically_equivalent(changed, new)
    else:
        changed = deepcopy(old.complete())
        candidate = changed["claim_candidates"]["c-a"]
        if field == "source.config":
            candidate["source"]["config"]["mutation"] = True
        else:
            candidate[field] = ["wrong-support"] if field == "supporting_events" else "wrong-subject"
        with pytest.raises(ValueError, match="equivalence"):
            forward.assert_semantically_equivalent_values(changed, new.complete())
