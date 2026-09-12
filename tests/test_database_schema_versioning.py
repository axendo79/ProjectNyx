"""ADR 0011: acceptance cases and connection-boundary regressions."""
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


META_DDL = """CREATE TABLE schema_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL CHECK (typeof(version) = 'integer' AND version > 0),
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL
)"""
VALID_ROW = (1, 4, "2026-09-08T00:00:00Z", "nyx/0.0.0")


def metadata_fixture(path, row=VALID_ROW, *, ddl=META_DDL, rows=None):
    # Test-only corruption: store the exact values without affinity conversions,
    # then restore the required DDL without rewriting records. New connections
    # see correct constraints/types and only the intended bad row value.
    # The INTEGER PRIMARY KEY remains real throughout: NULL/text IDs cannot be
    # represented by this SQLite layout and are not pretend integration cases.
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE schema_meta (id INTEGER PRIMARY KEY, version, created_at, created_by)")
        for value in (rows if rows is not None else ([] if row is None else [row])):
            conn.execute("INSERT INTO schema_meta VALUES (?, ?, ?, ?)", value)
        conn.execute("PRAGMA writable_schema=ON")
        conn.execute("UPDATE sqlite_master SET sql=? WHERE name='schema_meta'", (ddl,))
        conn.execute("PRAGMA writable_schema=OFF")
        conn.commit()



def refused_unchanged(path, reason, *, create=False, detail=None):
    before = snapshot(path)
    with pytest.raises(storage.SchemaCompatibilityError) as error:
        storage.init_db(path, create=create)
    assert error.value.reason == reason
    if detail is not None:
        assert detail in str(error.value)
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
        assert row[:2] == (1, 4)
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
        conn.execute("UPDATE schema_meta SET version = 5")  # no version-specific CHECK
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
    metadata_fixture(zero, (1, 0, "2026-09-08T00:00:00Z", "nyx/0.0.0"))
    refused_unchanged(zero, "zero_version")


@pytest.mark.parametrize("row", [
    None,
    (2, 1, "time", "software"),
    (1, None, "time", "software"),
    (1, 1, None, "software"),
    (1, 1, "time", None),
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
    metadata_fixture(path, row)
    if row is None:
        detail = "exactly one row"
    elif row[0] != 1:
        detail = "invalid ID"
    elif any(type(value) is not kind for value, kind in zip(row, (int, int, str, str))):
        detail = "metadata storage types"
    else:
        detail = "version must be positive"
    refused_unchanged(path, "malformed_metadata", detail=detail)
    # Prove that fixing only the intended row defect makes this schema pass.
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("DELETE FROM schema_meta")
        conn.execute("INSERT INTO schema_meta VALUES (?, ?, ?, ?)", VALID_ROW)
        conn.commit()
    storage.init_db(path).close()


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
    metadata_fixture(path, rows=[VALID_ROW, (2, *VALID_ROW[1:])])
    refused_unchanged(path, "malformed_metadata", detail="exactly one row")



@pytest.mark.parametrize("version, reason", [
    (0, "zero_version"), (1, "unsupported_version"), (2, "unsupported_version"),
    (3, "unsupported_version"), (5, "unsupported_version"),
])
def test_older_and_newer_versions(path, version, reason):
    # ADR 0025 extends refuse-and-preserve through version 3; no migration.
    metadata_fixture(path, (1, version, "time", "software"))
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
    metadata_fixture(replacement, (1, 5, "time", "software"))
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
    metadata_fixture(path, (1, 5, "time", "software"))
    before = snapshot(path)
    with pytest.raises(storage.SchemaCompatibilityError):
        record_observation(path, {
            "belief_id": "entity:test/property:value", "value": "one",
            "verifiability": "externally_checkable", "occurred_at": "2026-07-12T00:00:00Z",
            "source": {"actor_id": "sensor:test", "config": {}},
            "source_class": "direct_observation",
        })
    assert snapshot(path) == before


@pytest.mark.parametrize("name", ["sqliteX_existing", "sqliteexisting", "SQLITEX_existing"])
def test_unescaped_prefix_user_table_refuses(path, name):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(f'CREATE TABLE "{name}" (value TEXT)')
        conn.execute(f'INSERT INTO "{name}" VALUES (?)', ('existing data',))
        conn.commit()
    refused_unchanged(path, "nonempty_database", create=True)


@pytest.mark.parametrize("removed", [
    "CHECK (id = 1)", "CHECK (typeof(version) = 'integer' AND version > 0)",
])
def test_missing_required_check_refuses(path, removed):
    metadata_fixture(path, ddl=META_DDL.replace(removed, ""))
    refused_unchanged(path, "malformed_metadata", detail="CHECK constraints")


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_prohibited_version_check_refuses(path, version):
    metadata_fixture(path, ddl=META_DDL.replace("version INTEGER NOT NULL", f"version INTEGER NOT NULL CHECK(version = {version})"))
    refused_unchanged(path, "malformed_metadata", detail="CHECK constraints")


@pytest.mark.parametrize("extra", [
    "extra TEXT", "extra TEXT GENERATED ALWAYS AS (created_by) VIRTUAL",
    "extra TEXT GENERATED ALWAYS AS (created_by) STORED",
])
def test_extra_or_generated_column_refuses(path, extra):
    ddl = META_DDL[:-1] + ", " + extra + ")"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(ddl)
        conn.execute("INSERT INTO schema_meta(id, version, created_at, created_by) VALUES (?, ?, ?, ?)", VALID_ROW)
        conn.commit()
    refused_unchanged(path, "malformed_metadata", detail="four fields")


def test_generated_diagnostic_among_four_columns_refuses(path):
    ddl = META_DDL.replace("created_by TEXT NOT NULL", "created_by TEXT GENERATED ALWAYS AS ('nyx/0.0.0') VIRTUAL")
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(ddl)
        conn.execute("INSERT INTO schema_meta(id, version, created_at) VALUES (?, ?, ?)", VALID_ROW[:3])
        conn.commit()
    refused_unchanged(path, "malformed_metadata", detail="generated metadata columns")


def test_check_comparison_ignores_formatting_and_comments(path):
    ddl = META_DDL.replace("CHECK (id = 1)", 'check ([id] /* annotation */ = 1)').replace("typeof(version)", 'TYPEOF("version")')
    metadata_fixture(path, ddl=ddl)
    storage.init_db(path).close()


def test_check_text_in_comment_does_not_count(path):
    ddl = META_DDL.replace("CHECK (id = 1)", "/* CHECK (id = 1) */")
    metadata_fixture(path, ddl=ddl)
    refused_unchanged(path, "malformed_metadata", detail="CHECK constraints")
