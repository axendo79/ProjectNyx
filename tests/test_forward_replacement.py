"""Forward replacement uses Layer A order, preserving target records."""
from contextlib import closing
import pytest
from nyx import events, forward, projection, storage
from test_forward_correction import append, correction, initial_log
from test_reducer_boundary import T0, T2, claim, decoded, event, mention


def replacement(targets, cid="c-next", value="4200"):
    return {"claim": claim(cid, value=value), "targets": targets,
            "basis": {"kind": "stated", "statement": "state changed"}}


def simple_log():
    first = event(events.ENTITY_MENTION_RECORDED, mention())
    second = event(events.OBSERVATION_RECORDED, {"claims": [claim(value="4100")]}, 2, first)
    return [first, second]


def test_replacement_retention_cutoff_stale_and_earlier_time(tmp_path, monkeypatch):
    from nyx import transition_dependencies
    log = simple_log()
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in log: append(conn, pair)
        calls = []
        original = transition_dependencies.check_transition_dependencies
        def check(snapshot, ids):
            calls.append(tuple(ids))
            original(snapshot, ids)
        monkeypatch.setattr(transition_dependencies, "check_transition_dependencies", check)
        pair = event(events.CANDIDATE_REPLACED, replacement(["c-a"]), 3, log[-1], occurred_at=T0)
        append(conn, pair)
        after = storage.read_snapshot(conn, "3")
        candidates = after.belief("b-a")["claim_candidates"]
        assert {c["value"] for c in candidates if c["live_status"] == "live"} == {"4200"}
        assert storage.read_claim_candidate_value(conn, "c-a", "3") == "4100"
        assert storage.read_claim_candidate(conn, "c-a", "3")["live_status"] == "replaced"
        prior = projection.project_snapshot(decoded(log + [pair]), log[-1][0].recorded_at, "3")
        assert {c["value"] for c in prior.belief("b-a")["claim_candidates"]} == {"4100"}
        assert calls == [("c-a",), ("c-a",)]
        for kind, payload in ((events.CANDIDATE_REPLACED, replacement(["c-a"], "c-new")),
                              (events.CORRECTION_APPENDED, correction(["c-a"]))):
            stale = event(kind, payload, 4, pair)
            before = tuple(conn.iterdump())
            with pytest.raises(ValueError, match="live"):
                storage.safe_append_event(conn, *stale, "3")
            assert tuple(conn.iterdump()) == before
        assert after.complete() == projection.project_snapshot(decoded(log + [pair]), T2, "3").complete()
        forward.verify_lineage(decoded(log + [pair]), T2)


def test_report_replacement_refuses(tmp_path, monkeypatch):
    log = initial_log({"actor_id": "report", "config": {"report_vocabulary": "v1"}})
    snapshot = projection.project_snapshot(decoded(log), T2, "3")
    pair = event(events.CANDIDATE_REPLACED, replacement(["c-A"]), 3, log[-1])
    with pytest.raises(NotImplementedError, match="report"):
        projection.project_snapshot(decoded(log + [pair]), T2, "3")
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        ordinary = initial_log()
        for item in ordinary: append(conn, item)
        pair = event(events.CANDIDATE_REPLACED, replacement(["c-A"]), 3, ordinary[-1])
        monkeypatch.setattr(storage, "_read_snapshot", lambda *args: snapshot)
        before = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match="report"):
            storage.safe_append_event(conn, *pair, "3")
        assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("kind", ["correction", "replacement", "expiry"])
def test_transitions_accept_targets_whose_source_has_no_config(kind):
    # source.config is optional (integrity.py); its absence means not report-scoped.
    from test_forward_expiry import expiry
    log = initial_log({"actor_id": "user"})
    event_type, payload = {
        "correction": (events.CORRECTION_APPENDED, correction(["c-A"])),
        "replacement": (events.CANDIDATE_REPLACED, replacement(["c-A"])),
        "expiry": (events.CANDIDATE_EXPIRED, expiry(["c-A"])),
    }[kind]
    pair = event(event_type, payload, 3, log[-1])
    snapshot = projection.project_snapshot(decoded(log + [pair]), T2, "3")
    target = snapshot.record("claim_candidates", "c-A")
    assert target["live_status"] == {"correction": "corrected", "replacement": "replaced",
                                     "expiry": "expired"}[kind]
