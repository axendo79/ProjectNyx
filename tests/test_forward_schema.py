"""ADR 0035: explicit working-copy migration and immutable legacy opens."""
from contextlib import closing
import sqlite3

import pytest

from nyx import storage
from test_event_integrity import entries
from test_reducer_boundary import T2


def legacy(path):
    with closing(storage.init_db(path, create=True)) as conn, conn:
        conn.execute("DROP TABLE candidate_relations")
        conn.execute("UPDATE schema_meta SET version=4")


def test_copy_migration_and_selection(tmp_path):
    source, copy = tmp_path / "source.db", tmp_path / "copy.db"
    legacy(source)
    before = source.read_bytes()
    with closing(storage.open_readonly(source)) as conn:
        for projector_version in ("0", "1", "2"):
            storage.require_projector_schema(conn, projector_version)
        with pytest.raises(storage.SchemaCompatibilityError):
            storage.require_projector_schema(conn, "3")
        with closing(sqlite3.connect(copy)) as destination:
            conn.backup(destination)
    storage.migrate_working_copy(source, copy)
    assert source.read_bytes() == before
    with closing(storage.open_readonly(copy)) as conn:
        storage.require_projector_schema(conn, "3")
        assert conn.execute("SELECT version FROM schema_meta").fetchone() == (5,)
        assert conn.execute("SELECT count(*) FROM candidate_relations").fetchone() == (0,)


def test_migration_source_and_noncopy_refuse(tmp_path):
    source, copy = tmp_path / "source.db", tmp_path / "copy.db"
    legacy(source)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="distinct"):
        storage.migrate_working_copy(source, source)
    legacy(copy)
    with closing(sqlite3.connect(copy)) as conn, conn:
        conn.execute("UPDATE schema_meta SET created_by='different'")
    with pytest.raises(ValueError, match="copy"):
        storage.migrate_working_copy(source, copy)
    assert source.read_bytes() == before
    with closing(storage.open_readonly(copy)) as conn:
        assert conn.execute("SELECT version FROM schema_meta").fetchone() == (4,)


def test_migration_rolls_back_ddl_and_metadata(tmp_path, monkeypatch):
    source, copy = tmp_path / "source.db", tmp_path / "copy.db"
    legacy(source)
    with closing(storage.open_readonly(source)) as conn, closing(sqlite3.connect(copy)) as dest:
        conn.backup(dest)
    before = copy.read_bytes()
    monkeypatch.setattr(storage, "_RELATION_DDL", "CREATE TABLE injected(x); INVALID SQL;")
    with pytest.raises(sqlite3.DatabaseError):
        storage.migrate_working_copy(source, copy)
    assert copy.read_bytes() == before


@pytest.mark.parametrize("projector_version", ["0", "1", "2"])
def test_legacy_results_and_bytes(projector_version, tmp_path):
    old, fresh = tmp_path / "old.db", tmp_path / "fresh.db"
    legacy(old)
    storage.init_db(fresh, create=True).close()
    results, logs = [], []
    for path in (old, fresh):
        with closing(storage.init_db(path)) as conn:
            for pair in entries(projector_version):
                storage.safe_append_event(conn, *pair, projector_version)
                storage.materialize_pending(conn, T2, projector_version)
            results.append(storage.evaluate_whole_view(conn, T2, projector_version))
            logs.append(storage.read_all_events(conn))
    assert results[0] == results[1]
    assert logs[0] == logs[1]
    before = old.read_bytes()
    with closing(storage.open_readonly(old)) as conn:
        assert storage.evaluate_whole_view(conn, T2, projector_version) == results[0]
        with pytest.raises(storage.SchemaCompatibilityError):
            storage.require_projector_schema(conn, "3")
    assert old.read_bytes() == before
