"""ADR 0035 section 1: exactly two committed tables change in schema 5."""
from contextlib import closing
import sqlite3

import pytest

from nyx import storage
from test_event_integrity import entries
from test_reducer_boundary import T2


def schema_four(path):
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in entries("2"):
            storage.safe_append_event(conn, *pair, "2")
            storage.materialize_pending(conn, T2, "2")
        with conn:
            conn.execute("DROP TABLE candidate_relations")
            for table in ("committed_nodes", "committed_roots"):
                ddl = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
                conn.execute(ddl.replace(table, table + "_old", 1).replace(
                    "projector_version IN ('2', '3')", "projector_version = '2'"))
                conn.execute(f"INSERT INTO {table}_old SELECT * FROM {table}")
                conn.execute(f"DROP TABLE {table}")
                conn.execute(f"ALTER TABLE {table}_old RENAME TO {table}")
            conn.execute("UPDATE schema_meta SET version=4")


def test_fresh_committed_version_constraints(tmp_path):
    with closing(storage.init_db(tmp_path / "fresh.db", create=True)) as conn:
        with conn:
            conn.execute("INSERT INTO committed_nodes VALUES ('3','node','content')")
            conn.execute("INSERT INTO committed_roots VALUES ('3','beliefs','root')")
        for version in ("0", "1", "4", "unknown"):
            for table, values in (("committed_nodes", (version, "node", "content")),
                                  ("committed_roots", (version, "beliefs", "root"))):
                with pytest.raises(sqlite3.IntegrityError), conn:
                    conn.execute(f"INSERT INTO {table} VALUES (?,?,?)", values)


@pytest.mark.parametrize("fail", [False, True])
def test_exact_committed_table_migration(tmp_path, monkeypatch, fail):
    source, copy = tmp_path / "source.db", tmp_path / "copy.db"
    schema_four(source)
    before = source.read_bytes()
    with closing(storage.open_readonly(source)) as conn, closing(sqlite3.connect(copy)) as dest:
        conn.backup(dest)
        rows = {table: conn.execute(f"SELECT * FROM {table} ORDER BY 1,2").fetchall()
                for table in ("committed_nodes", "committed_roots")}
    copy_before = copy.read_bytes()
    if fail:
        monkeypatch.setattr(storage, "_RELATION_DDL", "CREATE TABLE injected(x); INVALID SQL;")
        with pytest.raises(sqlite3.DatabaseError):
            storage.migrate_working_copy(source, copy)
        assert copy.read_bytes() == copy_before
    else:
        storage.migrate_working_copy(source, copy)
        with closing(storage.open_readonly(copy)) as conn:
            for table, expected in rows.items():
                assert conn.execute(f"SELECT * FROM {table} ORDER BY 1,2").fetchall() == expected
                assert "IN ('2', '3')" in conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name=?", (table,)).fetchone()[0]
            assert storage.read_snapshot(conn, "2").beliefs() == storage.evaluate_whole_view(conn, T2, "2")
    assert source.read_bytes() == before
