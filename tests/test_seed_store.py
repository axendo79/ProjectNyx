"""Persistent demo fixtures use ingestion and preserve each projector contract."""

from contextlib import closing
from pathlib import Path
import runpy

import pytest

from nyx import events, ingestion, storage


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed_store.py"
seed_store = runpy.run_path(str(SCRIPT))["seed_store"]
AS_OF = "2026-07-14T00:00:00+00:00"


@pytest.mark.parametrize("version", ["0", "2"])
def test_fixture_is_deterministic_and_uses_ingestion(tmp_path, monkeypatch, version):
    submitted = []
    submit = ingestion.submit

    def record_submit(conn, pair, at, projector_version):
        submitted.append((pair[0].event_id, projector_version))
        return submit(conn, pair, at, projector_version)

    monkeypatch.setattr(ingestion, "submit", record_submit)
    first = seed_store(tmp_path / "first.sqlite", projector=version)
    second = seed_store(tmp_path / "second.sqlite", projector=version)
    assert {k: v for k, v in first.items() if k != "db"} == {k: v for k, v in second.items() if k != "db"}
    with closing(storage.open_readonly(first["db"])) as a, closing(storage.open_readonly(second["db"])) as b:
        log = storage.read_all_events(a)
        assert log == storage.read_all_events(b)
        assert sum(env.event_type == events.OBSERVATION_RECORDED for env, _ in log) == 8
        assert len(submitted) == 2 * len(log)
        if version == "2":
            assert {env.event_type for env, _ in log} == {events.ENTITY_MENTION_RECORDED, events.OBSERVATION_RECORDED}
            assert len(first["subject_ids"]) == len(first["mention_ids"]) == 3
            candidate_values = {c["value"] for c in storage.read_belief(a, "demo:alpha:ram", "2")["claim_candidates"]}
            assert len(candidate_values) >= 2
            pending = storage.read_belief_status(a, first["unpublished_belief"], "2")
            assert pending["belief"] is None and pending["stale"] is True
            assert pending["append_freshness"]["log_position"] == len(log)
            assert pending["derived_progress"]["log_position"] == len(log) - 1
            assert storage.read_belief_status(a, first["published_belief"], "2")["stale"] is False
            replay = storage.evaluate_whole_view(a, AS_OF, "2")
            assert first["unpublished_belief"] in replay
            assert storage.read_belief(a, first["unpublished_belief"], "2") is None
        else:
            assert {env.event_type for env, _ in log} == {events.OBSERVATION_RECORDED, events.CORRECTION_APPENDED}
            assert first["subject_ids"] == first["mention_ids"] == first["candidate_ids"] == []
            corrected = storage.read_belief_status(a, first["corrected_belief"], "0")
            assert corrected["belief"]["current_value"] == "512GB"
            assert corrected["belief"]["superseding_events"] == [log[-1][0].event_id]
            assert log[0][0].event_id in corrected["belief"]["supporting_events"]
            assert corrected["stale"] is False
            assert storage.read_projection_status(a, "0")["freshness_state"] == "fresh"
            assert storage.evaluate_whole_view(a, AS_OF, "0")[first["corrected_belief"]]["view_version_hash"] == corrected["belief"]["view_version_hash"]


@pytest.mark.parametrize("version", ["0", "2"])
def test_scaling_retains_structure_and_seed_is_repeatable(tmp_path, version):
    small = seed_store(tmp_path / "small.sqlite", projector=version, seed=17)
    large = seed_store(tmp_path / "large.sqlite", observations=12, projector=version, seed=17)
    repeat = seed_store(tmp_path / "repeat.sqlite", projector=version, seed=17)
    for key in ("belief_ids", "subject_ids", "mention_ids"):
        assert small[key] == large[key] == repeat[key]
    with closing(storage.open_readonly(small["db"])) as a, closing(storage.open_readonly(large["db"])) as b:
        assert len(storage.read_all_events(b)) - len(storage.read_all_events(a)) == 4
    with closing(storage.open_readonly(small["db"])) as a, closing(storage.open_readonly(repeat["db"])) as b:
        assert storage.read_all_events(a) == storage.read_all_events(b)


def test_existing_target_refuses_unchanged_and_force_is_explicit(tmp_path):
    path = tmp_path / "demo.sqlite"
    path.write_bytes(b"existing unrelated file")
    with pytest.raises(FileExistsError, match="--force"):
        seed_store(path)
    assert path.read_bytes() == b"existing unrelated file"
    created = seed_store(path, force=True)
    with closing(storage.open_readonly(path)) as conn:
        assert storage.read_store_metadata(conn)["event_count"] == created["event_count"]
    # Retained WAL/recovery files must never be deleted with the target.
    sidecar = Path(str(path) + "-wal")
    sidecar.write_bytes(b"unresolved recovery material")
    before = path.read_bytes()
    with pytest.raises(FileExistsError, match="sidecars"):
        seed_store(path, force=True)
    assert path.read_bytes() == before
    assert sidecar.read_bytes() == b"unresolved recovery material"


@pytest.mark.parametrize("options", [{"observations": 7}, {"projector": "1"}])
def test_invalid_options_refuse_before_touching_target(tmp_path, options):
    path = tmp_path / "demo.sqlite"
    with pytest.raises(ValueError):
        seed_store(path, **options)
    assert not path.exists()
