"""ADR 0009: historical knowledge, version dispatch, and deterministic views."""

from dataclasses import asdict, replace
from datetime import datetime, timezone

import pytest

from nyx import events, hashing, projection, storage
from nyx.skeleton import record_observation

BELIEF_ID = "entity:legion/property:ram"
T1 = "2026-07-12T12:00:00+00:00"
T2 = "2026-07-12T13:00:00+00:00"
T3 = "2026-07-12T14:00:00+00:00"


def make_event(recorded_at=T1, occurred_at=T1, value="64GB", previous=None,
               event_type=events.OBSERVATION_RECORDED, belief_id=BELIEF_ID):
    payload = {"belief_id": belief_id, "value": value,
               "verifiability": "externally_checkable"}
    envelope, _ = events.build_event(
        event_type=event_type, origin_type=events.ORIGIN_OBSERVED,
        source={"actor_id": "sensor:hwscan", "config": {}},
        source_class="direct_observation", occurred_at=occurred_at,
        payload=payload, prev_event_hash=previous,
    )
    # Set fixture log time before hashing; never rewrite a persisted envelope.
    envelope = replace(envelope, recorded_at=recorded_at)
    material = asdict(envelope)
    del material["event_hash"]
    del material["prev_event_hash"]
    envelope = replace(envelope, event_hash=hashing.event_hash(material, previous))
    return envelope, payload


def test_cutoff_bounds_recording_not_occurrence():
    first = make_event(occurred_at=T3)
    late = make_event(recorded_at=T2, occurred_at=T1, value="32GB",
                      previous=first[0].event_hash)
    result = projection.project([first, late], as_of=T1, projector_version="0")[BELIEF_ID]
    assert result["current_value"] == "64GB"
    assert result["supporting_events"] == [first[0].event_id]
    assert result["view_version_hash"] == hashing._sha256_hex(first[0].event_hash)
    assert result["projected_as_of"] == T1
    assert result["updated_at"] == T1


@pytest.mark.parametrize("recorded_at,included", [
    ("2026-07-12T12:00:00Z", True),
    ("2026-07-12T13:00:00+02:00", True),
    ("2026-07-12T09:00:00-05:00", False),
    ("2026-07-12T12:00:00.000001+00:00", False),
])
def test_cutoff_compares_instants_inclusively(recorded_at, included):
    result = projection.project([make_event(recorded_at=recorded_at)], T1, "0")
    assert (BELIEF_ID in result) is included
    if included:
        assert result[BELIEF_ID]["updated_at"] == recorded_at


def test_before_genesis_and_empty_log_have_no_beliefs():
    assert projection.project([make_event(recorded_at=T2)], T1, "0") == {}
    assert projection.project([], T1, "0") == {}


def test_equal_recording_times_preserve_log_order():
    first = make_event()
    second = make_event(value="128GB", previous=first[0].event_hash)
    result = projection.project([first, second], T1, "0")[BELIEF_ID]
    assert result["current_value"] == "128GB"
    assert result["supporting_events"] == [first[0].event_id, second[0].event_id]
    expected_hash = hashing._sha256_hex(
        hashing._sha256_hex(first[0].event_hash) + second[0].event_hash
    )
    assert result["view_version_hash"] == expected_hash


def test_later_correction_does_not_change_historical_view():
    first = make_event()
    correction = make_event(recorded_at=T3, occurred_at=T2, value="128GB",
                            previous=first[0].event_hash,
                            event_type=events.CORRECTION_APPENDED)
    log = [first, correction]
    historical = projection.project(log, T2, "0")[BELIEF_ID]
    corrected = projection.project(log, T3, "0")[BELIEF_ID]
    assert historical["current_value"] == "64GB"
    assert historical["superseding_events"] == []
    assert historical["updated_at"] == T1
    assert corrected["current_value"] == "128GB"
    assert corrected["superseding_events"] == [correction[0].event_id]
    assert corrected["updated_at"] == T3


def test_changing_cutoff_without_new_events_only_changes_evaluation_time():
    log = [make_event()]
    early = projection.project(log, T2, "0")[BELIEF_ID]
    later_cutoff = "2026-07-12T16:00:00+02:00"
    later = projection.project(log, later_cutoff, "0")[BELIEF_ID]
    assert early["projected_as_of"] == T2
    assert later == {**early, "projected_as_of": later_cutoff}


@pytest.mark.parametrize("version", ["1", "", "latest", 0, None])
def test_unsupported_versions_raise_even_for_empty_log(version):
    with pytest.raises(ValueError, match="Unsupported projector_version"):
        projection.project([], T1, version)


def test_version_registry_selects_fold(monkeypatch):
    calls = []
    original = projection.fold

    def selected_fold(prior, envelope, payload, as_of):
        calls.append(as_of)
        return original(prior, envelope, payload, as_of)

    monkeypatch.setitem(projection.PROJECTORS, "test-version", selected_fold)
    result = projection.project([make_event()], T2, "test-version")
    assert calls == [T2]
    assert result[BELIEF_ID]["projected_as_of"] == T2


@pytest.mark.parametrize("last_type,last_occurred_at,expected_value", [
    (events.OBSERVATION_RECORDED, T1, "64GB"),
    (events.CORRECTION_APPENDED, T3, "128GB"),
])
def test_fold_and_replay_are_byte_identical_without_clock(
    monkeypatch, last_type, last_occurred_at, expected_value
):
    first = make_event(occurred_at=T2)
    last = make_event(recorded_at=T2, occurred_at=last_occurred_at, value="128GB",
                      previous=first[0].event_hash, event_type=last_type)
    log = [first, last]
    before = [(asdict(envelope), dict(payload)) for envelope, payload in log]

    def forbidden_clock():
        pytest.fail("explicit evaluation time must not consult the clock")

    monkeypatch.setattr(projection, "_now_iso", forbidden_clock)
    incremental = None
    for envelope, payload in log:
        incremental = projection.fold(incremental, envelope, payload, as_of=T3)
    replay = projection.project(log, T3, "0")
    assert hashing.canonical_json(replay).encode() == hashing.canonical_json(
        {BELIEF_ID: incremental}
    ).encode()
    assert hashing.canonical_json(replay).encode() == hashing.canonical_json(
        projection.project(log, T3, "0")
    ).encode()
    assert incremental["current_value"] == expected_value
    assert incremental["projected_as_of"] == T3
    assert incremental["updated_at"] == T2
    assert [(asdict(envelope), payload) for envelope, payload in log] == before


def test_each_belief_keeps_last_recording_time_at_shared_evaluation_time():
    first = make_event()
    second = make_event(recorded_at=T2, belief_id="entity:legion/property:cpu",
                        previous=first[0].event_hash)
    result = projection.project([first, second], T3, "0")
    assert result[BELIEF_ID]["updated_at"] == T1
    assert result[second[1]["belief_id"]]["updated_at"] == T2
    assert all(belief["projected_as_of"] == T3 for belief in result.values())


def test_live_projection_defaults_to_one_current_time(monkeypatch):
    calls = []

    def current_time():
        calls.append(True)
        return T1

    monkeypatch.setattr(projection, "_now_iso", current_time)
    result = projection.project([make_event(), make_event(recorded_at=T2)],
                                projector_version="0")
    assert calls == [True]
    assert result[BELIEF_ID]["projected_as_of"] == T1
    assert len(result[BELIEF_ID]["supporting_events"]) == 1


def test_live_materialized_view_matches_replay(tmp_path):
    path = tmp_path / "nyx.db"
    before = datetime.now(timezone.utc)
    belief = record_observation(path, {
        "belief_id": BELIEF_ID, "value": "64GB",
        "verifiability": "externally_checkable", "occurred_at": T1,
        "source": {"actor_id": "sensor:hwscan", "config": {}},
        "source_class": "direct_observation",
    })
    after = datetime.now(timezone.utc)
    assert before <= datetime.fromisoformat(belief["projected_as_of"]) <= after
    conn = storage.init_db(path)
    try:
        log = storage.read_all_events(conn)
        assert belief["updated_at"] == log[-1][0].recorded_at
        assert projection.project(log, belief["projected_as_of"], "0") == {BELIEF_ID: belief}
    finally:
        conn.close()
