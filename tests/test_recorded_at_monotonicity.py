"""ADR 0010: recording-time monotonicity is enforced at append."""
from contextlib import closing
from dataclasses import asdict
from datetime import datetime

import pytest

from nyx import events, storage
from nyx.skeleton import record_observation


BASE = {
    "belief_id": "entity:test/property:value", "value": "one",
    "verifiability": "externally_checkable", "occurred_at": "2026-07-12T00:00:00Z",
    "source": {"actor_id": "sensor:test", "config": {}},
    "source_class": "direct_observation",
}


def clock(monkeypatch, timestamp):
    class FixedClock:
        @staticmethod
        def now(tz):
            return datetime.fromisoformat(timestamp)
    monkeypatch.setattr(events, "datetime", FixedClock)


def test_backward_clock_adjustment_at_append(tmp_path, monkeypatch):
    path = tmp_path / "nyx.db"
    storage.init_db(path, create=True).close()
    clock(monkeypatch, "2026-07-12T13:00:00Z")
    first = record_observation(path, BASE)
    with closing(storage.init_db(path)) as conn:
        before = tuple(conn.iterdump())
    clock(monkeypatch, "2026-07-12T12:00:00Z")
    with pytest.raises(storage.BackdatedRecordingError, match="precedes previous event"):
        record_observation(path, {**BASE, "value": "two"})
    with closing(storage.init_db(path)) as conn:
        assert tuple(conn.iterdump()) == before
        assert storage.read_belief(conn, BASE["belief_id"]) == first
        assert len(storage.read_all_events(conn)) == 1
    # Refusal released the connection and did not poison subsequent appends.
    clock(monkeypatch, "2026-07-12T14:00:00Z")
    assert record_observation(path, {**BASE, "value": "two"})["current_value"] == "two"


@pytest.mark.parametrize("timestamp, refused", [
    ("2026-07-12T13:00:00Z", False),
    ("2026-07-12T15:00:00+02:00", False),
    ("2026-07-12T14:00:00+02:00", True),
    ("2026-07-12T09:00:00-05:00", False),
])
def test_append_compares_instants_globally_and_does_not_rewrite(tmp_path, monkeypatch, timestamp, refused):
    path = tmp_path / "nyx.db"
    with closing(storage.init_db(path, create=True)) as conn:
        clock(monkeypatch, "2026-07-12T13:00:00Z")
        envelope, payload = events.build_event(
            event_type=events.OBSERVATION_RECORDED, origin_type=events.ORIGIN_OBSERVED,
            source=BASE["source"], source_class=BASE["source_class"],
            occurred_at=BASE["occurred_at"], prev_event_hash=None,
            payload={"belief_id": BASE["belief_id"], "value": "one", "verifiability": BASE["verifiability"]},
        )
        assert storage.safe_append_event(conn, envelope, payload)
        clock(monkeypatch, timestamp)
        second, second_payload = events.build_event(
            event_type=events.OBSERVATION_RECORDED, origin_type=events.ORIGIN_OBSERVED,
            source=BASE["source"], source_class=BASE["source_class"],
            occurred_at=BASE["occurred_at"], prev_event_hash=envelope.event_hash,
            payload={"belief_id": "entity:other/property:value", "value": "two", "verifiability": BASE["verifiability"]},
        )
        original = asdict(second)
        before = tuple(conn.iterdump())
        if refused:
            with pytest.raises(storage.BackdatedRecordingError):
                storage.safe_append_event(conn, second, second_payload)
            assert tuple(conn.iterdump()) == before
        else:
            assert storage.safe_append_event(conn, second, second_payload)
            assert [item[0].event_id for item in storage.read_all_events(conn)] == [envelope.event_id, second.event_id]
            assert storage.read_all_events(conn)[1][0].recorded_at == second.recorded_at
        assert asdict(second) == original
