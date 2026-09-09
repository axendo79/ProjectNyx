"""ADR 0014 stage one: independent legacy goldens and the new boundary."""

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from nyx import events, hashing, projection, reducer, skeleton, storage

T0 = "2026-07-12T00:00:00Z"
T1 = "2026-07-13T00:00:00Z"
T2 = "2026-07-14T00:00:00Z"
T3 = "2026-07-15T00:00:00Z"


def canonical(value):
    return hashing.canonical_json(value).encode("utf-8")


@pytest.fixture
def golden():
    # Captured from the unmodified projector before implementing stage one.
    return json.loads((Path(__file__).parent / "fixtures/version0_ordinary.json").read_text(encoding="utf-8"))


@pytest.fixture
def log(golden):
    return [(events.Envelope(**envelope), payload) for envelope, payload in golden["events"]]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "nyx.db"
    with closing(storage.init_db(path, create=True)) as conn:
        yield path, conn


def payload_row(envelope, payload):
    return events.Payload(envelope.payload_hash, envelope.event_id, None,
                          hashing.canonical_json(payload))


def append(conn, entry, version="0"):
    envelope, payload = entry
    return storage.safe_append_event(conn, envelope, payload_row(*entry), version)


def rehash(envelope, **changes):
    envelope = replace(envelope, **changes)
    material = asdict(envelope)
    del material["event_hash"], material["prev_event_hash"]
    return replace(envelope, event_hash=hashing.event_hash(material, envelope.prev_event_hash))


def contents(conn):
    return {key: json.loads(raw) for key, raw in conn.execute(
        "SELECT belief_id, content FROM projected_beliefs WHERE projector_version='1'"
    )}


def logical_db(conn):
    return tuple(conn.iterdump())


def test_version_zero_golden_bytes(golden, log, db):
    _, conn = db
    expected = golden["expected_canonical"].encode("utf-8")
    assert canonical(projection.project(log, T2, "0")) == expected
    for entry in log:
        append(conn, entry)
        envelope, payload = entry
        prior = storage.read_belief(conn, payload["belief_id"])
        storage.upsert_belief(conn, projection.fold(prior, envelope, payload, T2))
    live = {key: storage.read_belief(conn, key) for key in ("a", "b")}
    assert canonical(live) == expected
    assert canonical(storage.evaluate_whole_view(conn, T2, "0")) == expected
    # New-version publication never changes the legacy rows or Layer A bytes.
    legacy_rows = conn.execute("SELECT * FROM resolved_beliefs ORDER BY belief_id").fetchall()
    envelopes = conn.execute("SELECT * FROM events ORDER BY rowid").fetchall()
    storage.materialize_pending(conn, T2)
    assert conn.execute("SELECT * FROM resolved_beliefs ORDER BY belief_id").fetchall() == legacy_rows
    assert conn.execute("SELECT * FROM events ORDER BY rowid").fetchall() == envelopes
    assert canonical(projection.project(storage.read_all_events(conn), T2, "0")) == expected


def test_incremental_replay_and_ordinary_semantics_at_every_prefix(db, log):
    _, conn = db
    for index, entry in enumerate(log):
        append(conn, entry)
        assert storage.materialize_pending(conn, T2) == 1
        actual = contents(conn)
        assert canonical(actual) == canonical(projection.project(log[:index + 1], T2, "1"))
        legacy = projection.project(log[:index + 1], T2, "0")
        for key, view in actual.items():
            for field, value in legacy[key].items():
                if field == "view_version_hash":
                    assert view[field] != value
                elif field.endswith("_events"):
                    assert view[field] == hashing.canonical_set(value)
                else:
                    assert view[field] == value
        assert conn.execute("SELECT log_position, event_id FROM derived_progress").fetchone() == (
            index + 1, entry[0].event_id,
        )


def test_snapshot_is_detached_and_same_for_incremental_and_replay(db, log, monkeypatch):
    _, conn = db
    seen = []
    original = reducer.reduce
    def capture(snapshot, envelope, payload, as_of):
        seen.append((snapshot, envelope.event_id))
        return original(snapshot, envelope, payload, as_of)
    monkeypatch.setattr(reducer, "reduce", capture)
    for entry in log:
        append(conn, entry)
    storage.materialize_pending(conn, T2)
    live = [(s.log_position, s.event_id, s.beliefs(), event) for s, event in seen]
    saved = seen[1][0]
    mutable = saved.belief("a")
    mutable["supporting_events"].clear()
    assert saved.belief("a")["supporting_events"] == [log[0][0].event_id]
    assert saved.event(log[0][0].event_id)["payload"] == log[0][1]
    assert saved.belief("b") is None
    with pytest.raises(TypeError):
        saved._beliefs["x"] = "{}"
    seen.clear()
    projection.project(log, T2, "1")
    replay = [(s.log_position, s.event_id, s.beliefs(), event) for s, event in seen]
    assert canonical(live) == canonical(replay)


def test_lineage_exact_record_genesis_and_own_pre_event_dependency(log):
    beliefs = {}
    for index, (envelope, payload) in enumerate(log):
        key = payload["belief_id"]
        prior = beliefs.get(key)
        snapshot = reducer.Snapshot(beliefs, index, None if index == 0 else log[index - 1][0].event_id)
        delta = reducer.reduce(snapshot, envelope, payload, T2)
        assert delta.event_id == envelope.event_id
        assert set(delta.beliefs) == {key}
        view = delta.beliefs[key]
        expected = {
            "lineage_format": "nyx-belief-lineage/1", "projector_version": "1",
            "producing_event": {"event_id": envelope.event_id, "event_hash": envelope.event_hash},
            "predecessors": [] if prior is None else [{
                "belief_id": key, "view_version_hash": prior["view_version_hash"],
            }],
            "result": {k: v for k, v in view.items()
                       if k not in ("view_version_hash", "projected_as_of")},
        }
        assert view["view_version_hash"] == hashing._sha256_hex(hashing.canonical_json(expected))
        beliefs.update(delta.beliefs)
        assert snapshot.beliefs().get(key) == prior


@pytest.mark.parametrize("field", [
    "belief_id", "current_value", "value_occurred_at", "verification_state",
    "verifiability", "display_origin", "supporting_events", "opposing_events",
    "superseding_events", "resolution_basis", "event_dependencies", "updated_at",
])
def test_lineage_covers_every_ordinary_event_derived_field(log, field):
    view = projection.project(log, T2, "1")["a"]
    def digest(result):
        return canonical(hashing.belief_lineage("1", "event", "digest", [], result))
    changed = deepcopy(view)
    changed[field] = [] if field == "event_dependencies" else "changed"
    assert digest(changed) != digest(view)
    assert digest({**view, "projected_as_of": T3, "view_version_hash": "ignored"}) == digest(view)


def test_lineage_covers_sources_claims_and_timestamp_spelling(log):
    first, payload = log[0]
    baseline = projection.project([(first, payload)], T2, "1")["a"]
    for modified in (
        replace(first, source_class="different"),
        replace(first, source='{"actor_id":"different","config":{}}'),
        replace(first, occurred_at="2026-07-12T12:00:00+00:00"),
    ):
        # Hold event_hash fixed to establish explicit result coverage independently
        # of the producing event's global-chain commitment.
        view = projection.project([(modified, payload)], T2, "1")["a"]
        assert view["view_version_hash"] != baseline["view_version_hash"]


def test_canonical_sets_preserve_unicode_and_ordered_path_edges():
    members = [{"id": "é", "path": ["b", "a"]}, {"id": "😀", "path": ["a", "b"]}]
    expected = sorted(members, key=canonical)
    assert hashing.canonical_set(members[::-1] + members) == expected
    encoded = canonical(hashing.canonical_set(members))
    assert "é".encode() in encoded and "😀".encode() in encoded
    assert b'"path":["b","a"]' in encoded
    deps = [{"belief_id": "z", "view_version_hash": "2"},
            {"belief_id": "a", "view_version_hash": "1"}]
    assert canonical(hashing.belief_lineage("1", "e", "h", deps + deps, {})) == canonical(
        hashing.belief_lineage("1", "e", "h", deps[::-1], {}))


def test_projected_evidence_sets_canonicalize_input_order_and_duplicates(log):
    first = projection.project(log[:4], T2, "1")
    scrambled = deepcopy(first)
    for pool in ("supporting_events", "opposing_events", "superseding_events", "event_dependencies"):
        scrambled["a"][pool] = scrambled["a"][pool][::-1] * 2
    envelope, payload = log[4]
    one = reducer.reduce(reducer.Snapshot(first), envelope, payload, T2)
    two = reducer.reduce(reducer.Snapshot(scrambled), envelope, payload, T2)
    assert canonical(one.beliefs) == canonical(two.beliefs)


def test_cutoffs_time_only_lineage_and_unrelated_beliefs(log, db):
    _, conn = db
    early = log[:1]
    later = (rehash(log[1][0], recorded_at=T3), log[1][1])
    all_events = early + [later]
    for entry in all_events:
        append(conn, entry)
    assert projection.project(all_events, T0, "1") == {}
    assert canonical(projection.project(all_events, T2, "1")) == canonical(projection.project(early, T2, "1"))
    storage.materialize_pending(conn, T2)
    before = contents(conn)["a"]
    storage.materialize_pending(conn, T3)
    assert contents(conn)["a"] == before
    replay = projection.project(all_events, T3, "1")
    assert replay["a"] == {**before, "projected_as_of": T3}
    assert storage.read_belief_status(conn, "a")["stale"] is False


def test_append_freshness_separate_from_progress_and_lineage(db, log):
    _, conn = db
    append(conn, log[0])
    status = storage.read_belief_status(conn, "a")
    assert status["stale"] and status["belief"] is None
    assert status["derived_progress"] is None
    assert status["append_freshness"]["log_position"] == 1
    storage.materialize_pending(conn, T2)
    status = storage.read_belief_status(conn, "a")
    assert not status["stale"]
    assert status["belief"]["view_version_hash"] != status["append_freshness"]["event_hash"]
    append(conn, log[1])  # same recorded_at; unrelated belief
    assert storage.read_belief_status(conn, "a")["stale"] is False
    assert storage.read_belief_status(conn, "b")["stale"] is True
    append(conn, log[2])  # same recorded_at; newer event for a
    status = storage.read_belief_status(conn, "a")
    assert status["stale"]
    assert status["derived_progress"]["log_position"] == 1
    assert status["append_freshness"]["log_position"] == 3
    assert storage.read_belief(conn, "a", "1")["stale"] is True
    storage.materialize_pending(conn, T2)
    assert storage.read_belief(conn, "a", "1")["stale"] is False


@pytest.mark.parametrize("failure", ["before_progress", "after_progress"])
def test_atomic_publication_failure_and_consistent_reader(db, log, monkeypatch, failure):
    path, conn = db
    append(conn, log[0])
    storage.materialize_pending(conn, T2)
    old = storage.read_belief_status(conn, "a")
    append(conn, log[1])
    append(conn, log[2])
    before = logical_db(conn)
    with closing(storage.init_db(path)) as reader:
        if failure == "before_progress":
            conn.execute("CREATE TEMP TRIGGER fail_progress BEFORE UPDATE ON derived_progress "
                         "BEGIN SELECT RAISE(ABORT, 'publication failure'); END")
            expected_error = sqlite3.IntegrityError
        else:
            original = storage._publish_delta
            def fail(*args):
                original(*args)
                observed = storage.read_belief_status(reader, "a")
                assert observed["belief"] == old["belief"]
                assert observed["derived_progress"] == old["derived_progress"]
                assert observed["stale"]
                assert storage.read_belief_status(reader, "b")["belief"] is None
                raise RuntimeError("publication failure")
            monkeypatch.setattr(storage, "_publish_delta", fail)
            expected_error = RuntimeError
        with pytest.raises(expected_error, match="publication failure"):
            storage.materialize_pending(conn, T2)
        assert logical_db(conn) == before
        assert storage.read_belief_status(reader, "a")["belief"] == old["belief"]
    if failure == "before_progress":
        conn.execute("DROP TRIGGER fail_progress")
    else:
        monkeypatch.setattr(storage, "_publish_delta", original)
    assert storage.materialize_pending(conn, T2) == 2
    assert canonical(contents(conn)) == canonical(projection.project(log[:3], T2, "1"))


def test_retry_after_publication_does_not_reduce_or_append_again(db, log, monkeypatch):
    _, conn = db
    for entry in log:
        append(conn, entry)
    storage.materialize_pending(conn, T2)
    before = logical_db(conn)
    def forbidden(*args, **kwargs):
        pytest.fail("retry must not reduce or allocate IDs")
    monkeypatch.setattr(reducer, "reduce", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    assert storage.materialize_pending(conn, T3) == 0
    assert append(conn, log[0], "1") is False
    assert logical_db(conn) == before


def test_recovery_ignores_corrupt_partial_derived_snapshot(db, log, monkeypatch):
    _, conn = db
    for entry in log:
        append(conn, entry)
    with conn:
        conn.execute("INSERT INTO projected_beliefs VALUES ('1', 'bogus', '{}')")
        conn.execute("INSERT INTO derived_progress VALUES ('1', 999, 'bogus')")
    def forbidden(*args, **kwargs):
        pytest.fail("recovery must not trust derived snapshots or allocate IDs")
    monkeypatch.setattr(storage, "_read_snapshot", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    layer_a = conn.execute("SELECT * FROM events ORDER BY rowid").fetchall()
    expected = projection.project(log, T2, "1")
    assert canonical(storage.rebuild_projection(conn, T2)) == canonical(expected)
    assert canonical(contents(conn)) == canonical(expected)
    assert conn.execute("SELECT * FROM events ORDER BY rowid").fetchall() == layer_a
    before = logical_db(conn)
    storage.rebuild_projection(conn, T2)
    assert logical_db(conn) == before


def test_new_acceptance_requires_actual_prefix_and_refuses_backdating(db, log):
    _, conn = db
    append(conn, log[0], "1")
    before = logical_db(conn)
    with pytest.raises(storage.ProjectionBehindError):
        append(conn, log[1], "1")
    assert logical_db(conn) == before
    storage.materialize_pending(conn, T2)
    correction = (rehash(log[1][0], event_type=events.CORRECTION_APPENDED,
                         occurred_at=T0), {**log[1][1], "belief_id": "a"})
    before = logical_db(conn)
    with pytest.raises(projection.BackdatedCorrectionError):
        append(conn, correction, "1")
    assert logical_db(conn) == before
    with pytest.raises(projection.BackdatedCorrectionError):
        projection.project([log[0], correction], T2, "1")


def test_append_position_change_cannot_authorize_stale_acceptance(db, log):
    path, conn = db
    append(conn, log[0], "1")
    storage.materialize_pending(conn, T2)
    with closing(storage.init_db(path)) as concurrent:
        append(concurrent, log[1], "1")
        storage.materialize_pending(concurrent, T2)
    # Built at the first prefix; even a caught-up materialization cannot make its
    # old chain tip valid at the new append position.
    stale = (rehash(log[2][0], prev_event_hash=log[0][0].event_hash), log[2][1])
    before = logical_db(conn)
    with pytest.raises(ValueError, match="different append position"):
        append(conn, stale, "1")
    assert logical_db(conn) == before


@pytest.mark.parametrize("version", ["0", "1"])
@pytest.mark.parametrize("kind", [events.ENTITY_MERGE_ACCEPTED, events.ENTITY_SPLIT_ASSERTED])
def test_identity_events_refuse_loudly_without_belief_id(db, log, version, kind):
    _, conn = db
    envelope = rehash(log[0][0], event_type=kind)
    before = logical_db(conn)
    with pytest.raises(NotImplementedError, match=kind):
        projection.project([(envelope, {})], T2, version)
    with pytest.raises(NotImplementedError, match=kind):
        append(conn, (envelope, {}), version)
    assert logical_db(conn) == before


def test_unworked_origin_refuses_before_append(db, log):
    _, conn = db
    envelope = rehash(log[0][0], origin_type=events.ORIGIN_USER_STATED)
    before = logical_db(conn)
    with pytest.raises(NotImplementedError, match="origin"):
        append(conn, (envelope, log[0][1]), "1")
    assert logical_db(conn) == before


def test_ordinary_new_read_does_not_replay(db, log, monkeypatch):
    _, conn = db
    append(conn, log[0])
    storage.materialize_pending(conn, T2)
    def forbidden(*args, **kwargs):
        pytest.fail("ordinary read must not reconstruct")
    monkeypatch.setattr(projection, "project", forbidden)
    monkeypatch.setattr(storage, "read_all_events", forbidden)
    assert storage.read_belief(conn, "a", "1")["current_value"] == log[0][1]["value"]


def test_live_new_version_and_whole_view_equality(db):
    path, conn = db
    submission = {"belief_id": "opaque", "value": "測定 — 64GB", "verifiability": "externally_checkable",
                  "occurred_at": T1, "source": {"actor_id": "sensor", "config": {}},
                  "source_class": "direct_observation"}
    observed = skeleton.record_observation(path, submission, "1")
    assert not observed["stale"]
    assert skeleton.record_observation(path, submission, "1") == observed
    corrected = skeleton.record_correction(path, {**submission, "value": "128GB", "occurred_at": T2}, "1")
    assert corrected["current_value"] == "128GB"
    assert corrected["verification_state"] == "verified"
    assert not corrected["stale"]
    at = corrected["projected_as_of"]
    actual = {"opaque": {key: value for key, value in corrected.items() if key != "stale"}}
    assert canonical(actual) == canonical(storage.evaluate_whole_view(conn, at, "1"))
    assert storage.read_belief(conn, "opaque", "0") is None


def test_switching_live_versions_catches_up_without_changing_legacy_semantics(db):
    path, conn = db
    submission = {"belief_id": "opaque", "value": "one", "verifiability": "externally_checkable",
                  "occurred_at": T1, "source": {"actor_id": "sensor", "config": {}},
                  "source_class": "direct_observation"}
    for version, value in [("1", "one"), ("0", "two"), ("1", "three"), ("0", "four")]:
        result = skeleton.record_observation(path, {**submission, "value": value}, version)
        projected = {key: val for key, val in result.items() if key != "stale"}
        expected = storage.evaluate_whole_view(conn, result["projected_as_of"], version)
        assert canonical({"opaque": projected}) == canonical(expected)
    assert conn.execute("SELECT projector_version, log_position FROM derived_progress "
                        "ORDER BY projector_version").fetchall() == [("0", 4), ("1", 3)]
    assert storage.read_belief(conn, "opaque", "1")["stale"]


def test_version_one_database_with_existing_log_refuses_unchanged(db, log):
    path, conn = db
    append(conn, log[0])
    # A version-1 database has the unchanged legacy schema, without the two
    # stage-one derived tables. No automatic addition or stamping is allowed.
    with conn:
        conn.execute("DROP TABLE projected_beliefs")
        conn.execute("DROP TABLE derived_progress")
        conn.execute("UPDATE schema_meta SET version=1")
    before = logical_db(conn)
    with pytest.raises(storage.SchemaCompatibilityError, match="unsupported_version"):
        storage.init_db(path)
    assert logical_db(conn) == before


def test_append_failure_preserves_log_payload_and_freshness(db, log, monkeypatch):
    path, conn = db
    before = logical_db(conn)
    original = reducer.reduce
    with closing(storage.init_db(path)) as reader:
        def fail(snapshot, envelope, payload, as_of):
            original(snapshot, envelope, payload, as_of)
            assert reader.execute("SELECT count(*) FROM events").fetchone() == (0,)
            assert reader.execute("SELECT count(*) FROM entity_event_index").fetchone() == (0,)
            raise RuntimeError("acceptance failure")
        monkeypatch.setattr(reducer, "reduce", fail)
        with pytest.raises(RuntimeError, match="acceptance failure"):
            append(conn, log[0], "1")
    assert logical_db(conn) == before


def test_recovery_failure_keeps_previous_complete_publication(db, log, monkeypatch):
    _, conn = db
    for entry in log:
        append(conn, entry)
    storage.materialize_pending(conn, T2)
    before = logical_db(conn)
    original = reducer.reduce
    def fail(snapshot, envelope, payload, as_of):
        if envelope.event_id == log[2][0].event_id:
            raise RuntimeError("recovery failure")
        return original(snapshot, envelope, payload, as_of)
    monkeypatch.setattr(reducer, "reduce", fail)
    with pytest.raises(RuntimeError, match="recovery failure"):
        storage.rebuild_projection(conn, T2)
    assert logical_db(conn) == before


def test_reducer_never_samples_clock_or_allocates_ids(log, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("reduction is pure")
    monkeypatch.setattr(projection, "_now_iso", forbidden)
    monkeypatch.setattr(events, "new_event_id", forbidden)
    assert projection.project(log, T2, "1")
    with pytest.raises(ValueError, match="snapshot projector version"):
        reducer.reduce(reducer.Snapshot({}, projector_version="0"), *log[0], T2)


@pytest.mark.parametrize("kind", [events.VERIFICATION_COMPLETED, events.ENTITY_LINK_ACCEPTED])
def test_later_stage_events_are_not_implemented(db, log, kind):
    _, conn = db
    unsupported = (rehash(log[0][0], event_type=kind), log[0][1])
    with pytest.raises(NotImplementedError):
        projection.project([unsupported], T2, "1")
    with pytest.raises(NotImplementedError):
        append(conn, unsupported, "1")


def test_multi_belief_shared_time_equality_from_materialized_rows(db, log):
    _, conn = db
    append(conn, log[0])
    storage.materialize_pending(conn, T1)
    append(conn, log[1])
    storage.materialize_pending(conn, T2)
    raw = contents(conn)
    assert raw["a"]["projected_as_of"] != raw["b"]["projected_as_of"]
    # Valid for this time-independent ordinary reducer only (ADR 0012).
    evaluated = {key: {**view, "projected_as_of": T2} for key, view in raw.items()}
    expected = storage.evaluate_whole_view(conn, T2, "1")
    assert canonical(evaluated) == canonical(expected)
    assert canonical(raw) != canonical(expected)
