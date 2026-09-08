"""ADR 0012's seven acceptance cases, using live writes and full-field checks."""
from contextlib import closing
from datetime import datetime

import pytest

from nyx import events, hashing, projection, skeleton, storage

T0 = "2026-07-12T11:00:00+00:00"
T1 = "2026-07-12T12:00:00+00:00"
T2 = "2026-07-12T13:00:00+00:00"
T3 = "2026-07-12T14:00:00+00:00"
A = "entity:test/property:a"
B = "entity:test/property:b"


def set_clock(monkeypatch, timestamp):
    class Clock:
        @staticmethod
        def now(tz):
            return datetime.fromisoformat(timestamp)
    monkeypatch.setattr(events, "datetime", Clock)
    monkeypatch.setattr(skeleton, "datetime", Clock)


def submit(path, belief_id, value):
    return skeleton.record_observation(path, {
        "belief_id": belief_id, "value": value,
        "verifiability": "externally_checkable", "occurred_at": T1,
        "source": {"actor_id": "sensor:test", "config": {}},
        "source_class": "direct_observation",
    })


@pytest.fixture
def live(tmp_path, monkeypatch):
    path = tmp_path / "nyx.db"
    storage.init_db(path, create=True).close()
    set_clock(monkeypatch, T1)
    a = submit(path, A, "one")
    set_clock(monkeypatch, T2)
    b = submit(path, B, "two")
    with closing(storage.init_db(path)) as conn:
        yield path, conn, {A: a, B: b}


def serialized(view):
    return hashing.canonical_json(view).encode('utf-8')


def test_multiple_live_evaluation_times(live):
    _, conn, raw = live
    assert raw[A]["projected_as_of"] == T1
    assert raw[B]["projected_as_of"] == T2
    assert {key: storage.read_belief(conn, key) for key in raw} == raw
    evaluated = storage.evaluate_whole_view(conn, T2)
    assert all(row["projected_as_of"] == T2 for row in evaluated.values())
    assert serialized(raw) != serialized(evaluated)
    assert {key: storage.read_belief(conn, key) for key in raw} == raw


def test_shared_time_whole_view_equality(live):
    _, conn, raw = live
    evaluated = storage.evaluate_whole_view(conn, T3, "0")
    # Independent expected result from the actual live materialization for the
    # current time-independent reducer, not just project() compared with itself.
    expected = {key: {**row, "projected_as_of": T3} for key, row in raw.items()}
    assert serialized(evaluated) == serialized(expected)
    log = storage.read_all_events(conn)
    incremental = {}
    for envelope, payload in log:
        key = payload["belief_id"]
        incremental[key] = projection.fold(incremental.get(key), envelope, payload, T3)
    assert serialized(evaluated) == serialized(incremental)
    assert serialized(evaluated) == serialized(projection.project(log, T3, "0"))


def test_timestamp_discrepancy_is_observable(live):
    _, _, raw = live
    changed = {key: {**row, "projected_as_of": T3} for key, row in raw.items()}
    assert [r["view_version_hash"] for r in raw.values()] == [r["view_version_hash"] for r in changed.values()]
    assert [r["current_value"] for r in raw.values()] == [r["current_value"] for r in changed.values()]
    assert serialized(raw) != serialized(changed)


def test_historical_cutoff(live, monkeypatch):
    path, conn, raw = live
    set_clock(monkeypatch, T3)
    latest_a = submit(path, A, "changed later")
    historical = storage.evaluate_whole_view(conn, T1)
    assert serialized(historical) == serialized({A: raw[A]})
    assert B not in historical
    assert historical[A]["current_value"] == "one"
    assert historical[A]["supporting_events"] == raw[A]["supporting_events"]
    assert serialized(historical) == serialized(projection.project(storage.read_all_events(conn), T1, "0"))
    assert serialized(historical) != serialized({A: {**latest_a, "projected_as_of": T1}})
    assert storage.read_belief(conn, A) == latest_a
    assert storage.evaluate_whole_view(conn, T0) == {}


def test_current_time_independent_fields(live):
    _, conn, _ = live
    earlier = storage.evaluate_whole_view(conn, T2)
    later = storage.evaluate_whole_view(conn, T3)
    assert serialized(later) == serialized({key: {**row, "projected_as_of": T3} for key, row in earlier.items()})


def test_time_dependent_evaluation(live, monkeypatch):
    _, conn, raw = live
    calls = []
    def timed_fold(prior, envelope, payload, as_of):
        calls.append(as_of)
        result = projection.fold(prior, envelope, payload, as_of)
        result["evaluation_age_seconds"] = (
            datetime.fromisoformat(as_of) - datetime.fromisoformat(envelope.recorded_at)
        ).total_seconds()
        return result
    monkeypatch.setitem(projection.PROJECTORS, "time-test", timed_fold)
    earlier = storage.evaluate_whole_view(conn, T2, "time-test")
    calls.clear()
    later = storage.evaluate_whole_view(conn, T3, "time-test")
    assert calls == [T3, T3]
    assert later[A]["evaluation_age_seconds"] == 7200
    assert later[B]["evaluation_age_seconds"] == 3600
    assert serialized(later) != serialized({key: {**row, "projected_as_of": T3} for key, row in earlier.items()})
    assert serialized(later) == serialized(projection.project(storage.read_all_events(conn), T3, "time-test"))
    assert {key: storage.read_belief(conn, key) for key in raw} == raw


def test_determinism_and_layer_a_immutability(live, monkeypatch):
    _, conn, _ = live
    before = tuple(conn.iterdump())
    def forbidden_clock():
        pytest.fail("explicit evaluation must not sample the clock")
    monkeypatch.setattr(projection, "_now_iso", forbidden_clock)
    first = storage.evaluate_whole_view(conn, T3)
    second = storage.evaluate_whole_view(conn, T3)
    assert serialized(first) == serialized(second)
    assert tuple(conn.iterdump()) == before
    assert not conn.in_transaction


def test_ordinary_read_does_not_replay(live, monkeypatch):
    _, conn, raw = live
    def forbidden(*args, **kwargs):
        pytest.fail("ordinary materialized reads must not reconstruct")
    monkeypatch.setattr(projection, "project", forbidden)
    monkeypatch.setattr(storage, "read_all_events", forbidden)
    assert storage.read_belief(conn, A) == raw[A]


@pytest.mark.parametrize("timestamp", [None, 0, "invalid", "2026-07-12T12:00:00"])
def test_explicit_valid_time_required(live, timestamp):
    _, conn, _ = live
    with pytest.raises(ValueError):
        storage.evaluate_whole_view(conn, timestamp)


def test_unsupported_version_refuses(live):
    _, conn, _ = live
    with pytest.raises(ValueError, match="Unsupported projector_version"):
        storage.evaluate_whole_view(conn, T0, "unknown")
