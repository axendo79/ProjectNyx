"""F2: legacy acceptance requires the actual published append prefix."""

from contextlib import closing
from datetime import datetime, timedelta

import pytest

from nyx import projection, skeleton, storage, writer


AT = "2026-07-13T12:00:00+00:00"
THRESHOLD = timedelta(seconds=120)


def shifted(seconds):
    return (datetime.fromisoformat(AT) + timedelta(seconds=seconds)).isoformat()


def observation(seconds, value):
    return {"belief_id": "ram", "value": value,
            "verifiability": "externally_checkable", "occurred_at": shifted(seconds),
            "source": {"actor_id": "sensor", "config": {}},
            "source_class": "direct_observation"}


def request(raw, event_type="observation_recorded"):
    return writer.prepare_event(
        event_type=event_type, origin_type="observed", source=raw["source"],
        source_class=raw["source_class"], occurred_at=raw["occurred_at"],
        payload={key: raw[key] for key in ("belief_id", "value", "verifiability")})


def layer_a(conn):
    return (conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            storage.last_event_hash(conn))


@pytest.mark.parametrize("clock_step", [0, -100], ids=["stale-no-clock-step", "clamped-correction"])
def test_append_refuses_unpublished_prefix_without_caller_publication(tmp_path, clock_step):
    now = AT
    with closing(storage.init_db(tmp_path / "store.db", create=True,
                                 clock=lambda: now, threshold=THRESHOLD)) as conn:
        first = storage.append_submission(conn, request(observation(-10, "64GB")), "0")
        storage.materialize_pending(conn, AT, "0")
        now = shifted(clock_step)
        second_request = request(observation(10, "128GB"))
        second = storage.append_submission(conn, second_request, "0")
        assert second[0].recorded_at == first[0].recorded_at == AT
        assert second[0].prev_event_hash == first[0].event_hash
        # Leave the newer head unpublished. A backdated correction would pass
        # the belief-relative guard if acceptance trusted this older head.
        assert storage.read_belief(conn, "ram")["current_value"] == "64GB"
        before = layer_a(conn)
        assert before == (2, second[0].event_hash)
        attempted = (request(observation(0, "32GB"), "correction_appended")
                     if clock_step else request(observation(20, "256GB")))
        with pytest.raises(storage.ProjectionBehindError):
            storage.append_submission(conn, attempted, "0")
        assert layer_a(conn) == before
        # A committed retry is still valid while its publication is pending.
        assert storage.append_submission(conn, second_request, "0") == second
        assert layer_a(conn) == before


@pytest.mark.parametrize("progress", [None, (1, "wrong-event"), (2, "tip")])
def test_append_checks_both_progress_position_and_event_identity(tmp_path, progress):
    with closing(storage.init_db(tmp_path / "store.db", create=True,
                                 clock=lambda: AT, threshold=THRESHOLD)) as conn:
        tip = storage.append_submission(conn, request(observation(0, "64GB")), "0")
        storage.materialize_pending(conn, AT, "0")
        with conn:
            if progress is None:
                conn.execute("DELETE FROM derived_progress WHERE projector_version='0'")
            else:
                position, event_id = progress
                conn.execute(
                    "UPDATE derived_progress SET log_position=?,event_id=? WHERE projector_version='0'",
                    (position, tip[0].event_id if event_id == "tip" else event_id))
        before = layer_a(conn)
        with pytest.raises(storage.ProjectionBehindError):
            storage.append_submission(conn, request(observation(10, "128GB")), "0")
        assert layer_a(conn) == before


def test_skeleton_publishes_clamped_tip_and_refuses_backdated_correction(tmp_path, monkeypatch):
    path = tmp_path / "store.db"
    now = AT
    monkeypatch.setattr(writer, "clock_now", lambda: now)

    class Clock:
        @staticmethod
        def now(tz):
            return datetime.fromisoformat(now).astimezone(tz)

    monkeypatch.setattr(skeleton, "datetime", Clock)
    with closing(storage.init_db(path, create=True, threshold=THRESHOLD)) as conn:
        storage.append_submission(conn, request(observation(-10, "64GB")), "0")
        storage.materialize_pending(conn, AT, "0")
        now = shifted(-100)
        clamped = storage.append_submission(conn, request(observation(10, "128GB")), "0")
        assert clamped[0].recorded_at == AT

    # Pre-append publication must include the pending clamped observation;
    # post-append publication must also include the new clamped event.
    belief = skeleton.record_observation(path, observation(20, "256GB"))
    assert belief["current_value"] == "256GB"
    assert belief["projected_as_of"] == AT
    with closing(storage.open_readonly(path)) as conn:
        assert storage.read_projection_status(conn, "0")["stale"] is False
        before = layer_a(conn)
        assert before[0] == 3
    with pytest.raises(projection.BackdatedCorrectionError):
        skeleton.record_correction(path, observation(0, "32GB"))
    with closing(storage.open_readonly(path)) as conn:
        assert layer_a(conn) == before
        assert projection.project(storage.read_all_events(conn), AT, "0")["ram"] == belief
