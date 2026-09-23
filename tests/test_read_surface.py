"""Public read-only access, stored metadata and progress disclosure."""

from contextlib import closing
import sqlite3

import pytest

from nyx import projection, storage
from test_event_integrity import entries
from test_reducer_boundary import T2, decoded


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "store # with spaces.db"
    with closing(storage.init_db(path, create=True)) as conn:
        yield path, conn


def test_readonly_opener_reuses_validator_and_never_creates(store, tmp_path, monkeypatch):
    path, conn = store
    before = tuple(conn.iterdump())
    calls = []
    validator = storage._validate_schema

    def validate(reader):
        calls.append(reader.execute("PRAGMA query_only").fetchone()[0])
        validator(reader)

    monkeypatch.setattr(storage, "_validate_schema", validate)
    with closing(storage.open_readonly(path)) as reader:
        assert storage.read_store_metadata(reader) == {
            "schema_version": 4, "event_count": 0, "projector_versions": []}
    assert calls == [1]
    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        storage.open_readonly(missing)
    assert not missing.exists()
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("statement", [
    "DELETE FROM schema_meta", "UPDATE schema_meta SET version=5",
    "CREATE TABLE unexpected (x)", "CREATE TEMP TABLE unexpected (x)",
    "PRAGMA query_only=OFF", "PRAGMA user_version=5", "PRAGMA journal_mode=WAL",
    "ATTACH DATABASE ':memory:' AS other", "VACUUM", "PRAGMA wal_checkpoint(TRUNCATE)",
])
def test_readonly_refuses_writes_and_escape_hatches(store, statement):
    path, conn = store
    before = tuple(conn.iterdump())
    with closing(storage.open_readonly(path)) as reader:
        with pytest.raises(sqlite3.DatabaseError):
            reader.execute(statement)
    assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("damage", ["DELETE FROM schema_meta", "UPDATE schema_meta SET version=999"])
def test_readonly_schema_refusal_is_unchanged(store, damage):
    path, conn = store
    with conn:
        conn.execute(damage)
    before = tuple(conn.iterdump())
    conn.close()
    with pytest.raises(storage.SchemaCompatibilityError) as writable:
        storage.init_db(path)
    with pytest.raises(storage.SchemaCompatibilityError) as readonly:
        storage.open_readonly(path)
    assert (readonly.value.reason, str(readonly.value)) == (writable.value.reason, str(writable.value))
    with closing(sqlite3.connect(path)) as inspect:
        assert tuple(inspect.iterdump()) == before


@pytest.mark.parametrize("version", ["0", "1", "2"])
def test_metadata_and_freshness_before_and_after_publication(store, version):
    path, writer = store
    log = entries(version)
    for pair in log[:2]:
        storage.safe_append_event(writer, *pair, version)
        storage.materialize_pending(writer, T2, version)
    with closing(storage.open_readonly(path)) as reader:
        metadata = storage.read_store_metadata(reader)
        assert metadata == {"schema_version": 4, "event_count": 2,
                            "projector_versions": ["0"] if version == "0" else ["1", "2"]}
        assert storage.read_projection_status(reader, version)["stale"] is False
        assert storage.read_belief_status(reader, "b-a", version)["stale"] is False
        if version != "0":
            other = "2" if version == "1" else "1"
            assert storage.read_projection_status(reader, other)["stale"] is True
        storage.safe_append_event(writer, *log[2], version)
        pending = storage.read_belief_status(reader, "b-a", version)
        assert pending["stale"] is True
        assert pending["derived_progress"]["log_position"] == 2
        assert pending["append_freshness"]["log_position"] == 3
        storage.materialize_pending(writer, T2, version)
        assert storage.read_belief_status(reader, "b-a", version)["stale"] is False


def test_legacy_without_progress_is_unknown_without_replay(store, monkeypatch):
    path, conn = store
    pair = entries("0")[0]
    storage.safe_append_event(conn, *pair)
    belief = projection.project(decoded([pair]), T2)["b-a"]
    storage.upsert_belief(conn, belief)  # Existing raw API does not record a checkpoint.
    before = tuple(conn.iterdump())

    def forbidden(*args, **kwargs):
        pytest.fail("materialized freshness must not replay")

    monkeypatch.setattr(projection, "project", forbidden)
    with closing(storage.open_readonly(path)) as reader:
        status = storage.read_belief_status(reader, "b-a", "0")
        assert status["belief"] == storage.read_belief(reader, "b-a", "0")
        assert status["stale"] is None
        assert status["freshness_state"] == "unknown"
        assert status["derived_progress"] is None
        assert status["append_freshness"]["event_id"] == pair[0].event_id
        assert storage.read_projection_status(reader, "0")["stale"] is None
    assert tuple(conn.iterdump()) == before


def test_readonly_sees_live_wal_and_retains_consistent_snapshot(store):
    path, writer = store
    with closing(storage.open_readonly(path)) as reader:
        reader.execute("BEGIN")
        assert storage.read_store_metadata(reader)["event_count"] == 0
        storage.safe_append_event(writer, *entries("0")[0])
        assert storage.read_store_metadata(reader)["event_count"] == 0
        reader.commit()
        assert storage.read_store_metadata(reader)["event_count"] == 1


def test_metadata_does_not_report_registered_but_absent_versions(store):
    _, conn = store
    with conn:
        conn.execute("INSERT INTO committed_nodes VALUES ('2',?,?)", ("a" * 64, "{}"))
    assert storage.read_store_metadata(conn)["projector_versions"] == ["2"]


@pytest.mark.parametrize("version", ["1", "2"])
def test_unproven_projection_is_not_reported_fresh(store, version):
    _, conn = store
    with conn:
        conn.execute("INSERT INTO projected_beliefs VALUES (?, 'b-a', '{}')", (version,))
    assert storage.read_projection_status(conn, version)["stale"] is True


def test_legacy_unpublished_absence_and_invalid_progress(store):
    _, conn = store
    storage.safe_append_event(conn, *entries("0")[0])
    status = storage.read_belief_status(conn, "b-a", "0")
    assert status["belief"] is None and status["stale"] is True
    storage.materialize_pending(conn, T2, "0")
    with conn:
        conn.execute("UPDATE derived_progress SET event_id='missing' WHERE projector_version='0'")
    assert storage.read_projection_status(conn, "0")["stale"] is True
    assert storage.read_belief_status(conn, "b-a", "0")["stale"] is True
