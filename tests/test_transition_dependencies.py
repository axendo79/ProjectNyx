"""Closed recorded dependency predicate in ADR 0035 section 2."""
from copy import deepcopy

import pytest

from nyx import projection, reducer
from test_event_integrity import entries
from test_reducer_boundary import T2, decoded


def ordinary():
    return projection.project_snapshot(decoded(entries("2")), T2, "2").complete()


def snapshot(records):
    return reducer.Snapshot(**records, projector_version="3")


@pytest.mark.parametrize("field, value", [
    ("verification_basis", {"kind": "approval"}),
    ("predecessors", ["c-next"]),
    ("restrictions", ["restriction"]),
    ("opposing_events", ["opposition"]),
])
def test_target_dependency_refuses(field, value):
    from nyx.transition_dependencies import check_transition_dependencies
    records = ordinary()
    records["claim_candidates"]["c-a"][field] = value
    view = snapshot(records)
    before = view.complete()
    with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
        check_transition_dependencies(view, ["c-a"])
    assert view.complete() == before


@pytest.mark.parametrize("field", ["predecessors", "restrictions"])
def test_candidate_naming_target_refuses(field):
    from nyx.transition_dependencies import check_transition_dependencies
    records = ordinary()
    records["claim_candidates"]["c-next"][field] = ["c-a"]
    with pytest.raises(NotImplementedError, match="ADR 0015 section 5"):
        check_transition_dependencies(snapshot(records), ["c-a"])


def test_ordinary_targets_pass_and_are_checked():
    from nyx.transition_dependencies import check_transition_dependencies
    view = snapshot(ordinary())
    before, calls = deepcopy(view.complete()), []

    class Witness:
        def record(self, kind, identifier):
            calls.append((kind, identifier))
            return view.record(kind, identifier)

        def records(self, kind):
            calls.append((kind, "all"))
            return view.records(kind)

    check_transition_dependencies(Witness(), ["c-a", "c-next"])
    assert calls == [("claim_candidates", "c-a"), ("claim_candidates", "c-next"),
                     ("claim_candidates", "all")]
    assert view.complete() == before


def test_superseding_history_is_not_a_dependency():
    from nyx.transition_dependencies import check_transition_dependencies
    records = ordinary()
    records["claim_candidates"]["c-a"]["superseding_events"] = ["ending-event"]
    check_transition_dependencies(snapshot(records), ["c-a"])
