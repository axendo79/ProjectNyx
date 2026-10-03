"""RV1: live callers publish their committed prefix at a post-append time."""

from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from nyx import ingestion, integrity, projection, skeleton, storage, writer


REAL_CLOCK = writer.clock_now
OCCURRED = "2026-07-13T12:00:00Z"
SOURCE = {"actor_id": "live-test", "config": {}}


@pytest.fixture
def advancing_clock(monkeypatch, fixed_writer_clock):
    """Override the autouse fixture locally with advancing real wall time."""
    samples = []

    def clock():
        stamp = REAL_CLOCK()
        while samples and datetime.fromisoformat(stamp) <= datetime.fromisoformat(samples[-1]):
            stamp = REAL_CLOCK()
        samples.append(stamp)
        return stamp

    monkeypatch.setattr(writer, "clock_now", clock)
    return samples


def mention(conn, name):
    return ingestion.prepare_mention(
        conn, mention_id=f"m-{name}", subject_id=f"s-{name}", text=name,
        source=SOURCE, source_class="direct_observation", occurred_at=OCCURRED,
        origin_type="observed", event_id=f"e-{name}")


@pytest.mark.parametrize("projector_version", ["1", "2"])
@pytest.mark.parametrize("tip_ahead", [False, True])
@pytest.mark.parametrize("operation", ["mention", "observation"])
def test_live_result_equals_replay_at_publication_time(
        tmp_path, monkeypatch, advancing_clock, projector_version, tip_ahead, operation):
    path = tmp_path / "live.db"
    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    with closing(storage.init_db(path, create=True)) as conn:
        if tip_ahead or operation == "observation":
            if tip_ahead:
                conn.clock = lambda: future
            ingestion.submit(conn, mention(conn, "prior"), future, projector_version)
        if operation == "mention":
            request = mention(conn, "new")
        else:
            request = ingestion.prepare_observation(
                conn, claims=[{
                    "belief_id": "b-live", "claim_candidate_id": "c-live",
                    "mention_id": "m-prior", "subject_id": "s-prior",
                    "property_id": "P", "value": "live", "verifiability": "externally_checkable",
                }], source=SOURCE, source_class="direct_observation", occurred_at=OCCURRED,
                event_id="e-observation", projector_version=projector_version)

    publications = []
    materialize = storage.materialize_pending

    def capture(conn, as_of, projector_version):
        publications.append(as_of)
        return materialize(conn, as_of, projector_version)

    monkeypatch.setattr(storage, "materialize_pending", capture)
    record = skeleton.record_mention if operation == "mention" else skeleton.record_observation
    result = record(path, request, projector_version)
    assert result is not None
    with closing(storage.open_readonly(path)) as conn:
        assert not storage.read_projection_status(conn, projector_version)["stale"]
        log = storage.read_all_events(conn)
        as_of = publications[-1]
        assert datetime.fromisoformat(as_of) >= datetime.fromisoformat(log[-1][0].recorded_at)
        if tip_ahead:
            assert log[-1][0].recorded_at == future
            assert datetime.fromisoformat(future) > datetime.fromisoformat(advancing_clock[-1])
        replay = projection.project_snapshot(log, as_of, projector_version)
        if operation == "mention":
            assert result == replay.record("mentions", "m-new")
        else:
            assert result == {"b-live": {**replay.belief("b-live"), "stale": False}}


@pytest.mark.parametrize("projector_version", ["1", "2"])
def test_submit_preserves_explicit_historical_cutoff(tmp_path, advancing_clock, projector_version):
    with closing(storage.init_db(tmp_path / "historical.db", create=True)) as conn:
        committed = ingestion.submit(conn, mention(conn, "historical"), OCCURRED, projector_version)
        assert datetime.fromisoformat(committed[0].recorded_at) > datetime.fromisoformat(OCCURRED)
        assert storage.read_projection_status(conn, projector_version)["derived_progress"] is None
        assert projection.project_snapshot(
            [(committed[0], integrity.decode_payload(*committed))], OCCURRED,
            projector_version).record("mentions", "m-historical") is None
