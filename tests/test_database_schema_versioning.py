"""ADR 0011: ten acceptance cases and connection-boundary regressions."""
from contextlib import closing
from datetime import datetime, timezone
import sqlite3

import pytest

from nyx import projection, storage
from nyx.skeleton import record_observation


@pytest.fixture
def path(tmp_path):
    return tmp_path / "nyx.db"


def snapshot(path):
    with closing(sqlite3.connect(path)) as conn:
        return tuple(conn.iterdump())


def legacy(path, row=(1, 1, "2026-09-08T00:00:00Z", "nyx/0.0.0")):
    # No affinities: malformed legacy storage types must not be coerced by tests.
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE schema_meta (id, version, created_at, created_by)")
        if row is not None:
            conn.execute("INSERT INTO schema_meta VALUES (?, ?, ?, ?)", row)
        conn.commit()


def refused_unchanged(path, reason, *, create=False):
    before = snapshot(path)
    with pytest.raises(storage.SchemaCompatibilityError) as error:
        storage.init_db(path, create=create)
    assert error.value.reason == reason
    assert snapshot(path) == before


@pytest.mark.parametrize("existing", ["absent", "zero-byte", "empty-sqlite"])
def test_fresh_initialization(path, existing):
    if existing == "zero-byte":
        path.touch()
    elif existing == "empty-sqlite":
        with closing(sqlite3.connect(path)) as conn:
            conn.execute("VACUUM")
    before = datetime.now(timezone.utc)
    with closing(storage.init_db(path, create=True)) as conn:
        row = conn.execute("SELECT * FROM schema_meta").fetchone()
        assert row[:2] == (1, 1)
        assert before <= datetime.fromisoformat(row[2]) <= datetime.now(timezone.utc)
        assert datetime.fromisoformat(row[2]).utcoffset().total_seconds() == 0
        assert row[3] == "nyx/0.0.0"
        assert conn.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert conn.execute("SELECT count(*) FROM events").fetchone() == (0,)
        assert not conn.in_transaction
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO schema_meta VALUES (2, 1, 'time', 'software')")
        conn.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE schema_meta SET version = 0")
        conn.rollback()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE schema_meta SET version = 1.5")
        conn.rollback()
        conn.execute("UPDATE schema_meta SET version = 2")  # no CHECK(version = 1)
        conn.rollback()


def test_supported_reopen(path):
    storage.init_db(path, create=True).close()
    before = snapshot(path)
    bytes_before = path.read_bytes()
    for _ in range(2):
        storage.init_db(path).close()
    assert snapshot(path) == before
    assert path.read_bytes() == bytes_before


@pytest.mark.parametrize("recognizable", [False, True])
def test_unversioned_existing_database(path, recognizable):
    with closing(sqlite3.connect(path)) as conn:
        if recognizable:
            script = storage._SCHEMA_PATH.read_text(encoding="utf-8")
            conn.executescript(script)
            conn.execute("DROP TABLE schema_meta")
            conn.commit()
    refused_unchanged(path, "missing_metadata")


def test_missing_versus_zero(path, tmp_path):
    sqlite3.connect(path).close()
    refused_unchanged(path, "missing_metadata")
    zero = tmp_path / "zero.db"
    legacy(zero, (1, 0, "2026-09-08T00:00:00Z", "nyx/0.0.0"))
    refused_unchanged(zero, "zero_version")


@pytest.mark.parametrize("row", [
    None,
    (2, 1, "time", "software"),
    (None, 1, "time", "software"),
    (1, None, "time", "software"),
    (1, 1, None, "software"),
    (1, 1, "time", None),
    ("1", 1, "time", "software"),
    (1, "1", "time", "software"),
    (1, 1.0, "time", "software"),
    (1, 1.5, "time", "software"),
    (1, -1, "time", "software"),
    (1, b"1", "time", "software"),
    (1, 1, 42, "software"),
    (1, 1, "time", 42),
    (1, 1, b"time", "software"),
    (1, 1, "time", b"software"),
])
def test_malformed_metadata(path, row):
    legacy(path, row)
    refused_unchanged(path, "malformed_metadata")


@pytest.mark.parametrize("ddl", [
    "CREATE VIEW schema_meta AS SELECT 1 AS id, 1 AS version, 'time' AS created_at, 'software' AS created_by",
    "CREATE TABLE schema_meta (version INTEGER)",
    "CREATE TABLE schema_meta (id, version, created_at, created_by, extra)",
])
def test_structurally_invalid_metadata(path, ddl):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(ddl)
    refused_unchanged(path, "malformed_metadata")


def test_multiple_metadata_rows(path):
    legacy(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("INSERT INTO schema_meta VALUES (2, 1, 'time', 'software')")
        conn.commit()
    refused_unchanged(path, "malformed_metadata")


@pytest.mark.parametrize("version, reason", [(0, "zero_version"), (2, "unsupported_version")])
def test_older_and_newer_versions(path, version, reason):
    # Version 1 is the first positive version; explicit zero is the older case.
    legacy(path, (1, version, "time", "software"))
    refused_unchanged(path, reason)


@pytest.mark.parametrize("failure", ["schema", "insert", "validation"])
def test_failed_fresh_initialization(path, tmp_path, monkeypatch, failure):
    if failure in {"schema", "insert"}:
        script = storage._SCHEMA_PATH.read_text(encoding="utf-8")
        if failure == "schema":
            script += "\nTHIS IS NOT SQL;\n"
        else:
            script += "\nCREATE TRIGGER reject_meta BEFORE INSERT ON schema_meta BEGIN SELECT RAISE(ABORT, 'injected'); END;\n"
        broken = tmp_path / "broken.sql"
        broken.write_text(script, encoding="utf-8")
        monkeypatch.setattr(storage, "_SCHEMA_PATH", broken)
    else:
        def fail(conn):
            # Schema and metadata must still be invisible to another connection.
            with closing(sqlite3.connect(path)) as observer:
                assert observer.execute("SELECT count(*) FROM sqlite_master").fetchone() == (0,)
            raise RuntimeError("injected validation failure")
        monkeypatch.setattr(storage, "_validate_schema", fail)
    with pytest.raises((sqlite3.DatabaseError, RuntimeError)):
        storage.init_db(path, create=True)
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT count(*) FROM sqlite_master").fetchone() == (0,)
    # Failure closes its connection and releases locks; no partial initialization.
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("BEGIN EXCLUSIVE")
        conn.rollback()


def test_repeated_init_detects_substitution(path, tmp_path):
    storage.init_db(path, create=True).close()
    replacement = tmp_path / "replacement.db"
    legacy(replacement, (1, 2, "time", "software"))
    replacement.replace(path)
    refused_unchanged(path, "unsupported_version")


def test_fold_versus_replay_equality(path):
    storage.init_db(path, create=True).close()
    belief = record_observation(path, {
        "belief_id": "entity:test/property:value", "value": "one",
        "verifiability": "externally_checkable", "occurred_at": "2026-07-12T00:00:00Z",
        "source": {"actor_id": "sensor:test", "config": {}},
        "source_class": "direct_observation",
    })
    with closing(storage.init_db(path)) as conn:
        assert projection.project(storage.read_all_events(conn), belief["projected_as_of"], "0") == {
            belief["belief_id"]: storage.read_belief(conn, belief["belief_id"])
        }
        assert conn.execute("SELECT count(*) FROM events").fetchone() == (1,)


@pytest.mark.parametrize("kind", ["supported", "unversioned", "view"])
def test_create_nonempty_refuses(path, kind):
    if kind == "supported":
        storage.init_db(path, create=True).close()
    else:
        with closing(sqlite3.connect(path)) as conn:
            conn.execute("CREATE VIEW v AS SELECT 1" if kind == "view" else "CREATE TABLE events (id)")
    refused_unchanged(path, "nonempty_database", create=True)


def test_ordinary_open_never_creates(path):
    with pytest.raises(sqlite3.OperationalError):
        storage.init_db(path)
    assert not path.exists()


def test_write_connection_validates_before_use(path):
    legacy(path, (1, 2, "time", "software"))
    before = snapshot(path)
    with pytest.raises(storage.SchemaCompatibilityError):
        record_observation(path, {
            "belief_id": "entity:test/property:value", "value": "one",
            "verifiability": "externally_checkable", "occurred_at": "2026-07-12T00:00:00Z",
            "source": {"actor_id": "sensor:test", "config": {}},
            "source_class": "direct_observation",
        })
    assert snapshot(path) == before
