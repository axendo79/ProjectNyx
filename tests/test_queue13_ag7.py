"""A-G7: every unrelated table's DDL is byte-preserved, ADR 0035 §1."""
from contextlib import closing
import sqlite3
from nyx import storage
from test_committed_schema_amendment import schema_four


def ddl(conn):
    return {name: sql.encode("utf-8") for name, sql in conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")}


def test_ag7_schema5_migration_preserves_all_unrelated_ddl_bytes(tmp_path):
    source, copy = tmp_path / "schema4.db", tmp_path / "schema5.db"
    schema_four(source)
    with closing(storage.init_db(source)) as conn:
        # Preserve layout, quoting and constraint text, not normalized SQL.
        with conn:
            conn.execute('CREATE TABLE "fixture_unrelated" (\n  "key" TEXT PRIMARY KEY,\n  value TEXT CHECK(length(value)>0)\n)')
            conn.execute('INSERT INTO "fixture_unrelated" VALUES (?,?)', ("unrelated", "data"))
        before = ddl(conn)
        with closing(sqlite3.connect(copy)) as dest:
            conn.backup(dest)
    original_bytes = source.read_bytes()
    storage.migrate_working_copy(source, copy)
    with closing(storage.open_readonly(copy)) as conn:
        after = ddl(conn)
        assert set(after) == set(before) | {"candidate_relations"}
        for table in set(before) - {"committed_nodes", "committed_roots"}:
            assert after[table] == before[table], table
        assert conn.execute('SELECT * FROM "fixture_unrelated"').fetchall() == [("unrelated", "data")]
        for table in ("committed_nodes", "committed_roots"):
            assert after[table] != before[table]
            assert b"IN ('2', '3')" in after[table]
    assert source.read_bytes() == original_bytes
