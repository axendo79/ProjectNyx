"""B15: historical rebuild rows are isolated, ADR 0034 §§1,10."""
from contextlib import closing
from nyx import projection, storage
from test_forward_correction import append
from test_forward_reads import transition_log
from test_reducer_boundary import decoded


def version_rows(conn, version):
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return {table: sorted(conn.execute(f'SELECT * FROM "{table}" WHERE projector_version=?', (version,)).fetchall(), key=repr)
            for table in tables
            if "projector_version" in {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}}


def test_b15_rebuild_preserves_other_version_rows_and_progress(tmp_path):
    log = transition_log()
    with closing(storage.init_db(tmp_path / "versions.db", create=True)) as conn:
        for pair in log:
            append(conn, pair)
        complete_three = version_rows(conn, "3")
        cutoff = log[1][0].recorded_at
        storage.rebuild_projection(conn, cutoff, "2")
        assert version_rows(conn, "3") == complete_three
        frozen_two = version_rows(conn, "2")
        assert storage.read_snapshot(conn, "2").log_position == 2
        for cutoff in [pair[0].recorded_at for pair in log[1:]]:
            storage.rebuild_projection(conn, cutoff, "3")
            assert version_rows(conn, "2") == frozen_two
            expected = projection.project_snapshot(decoded(log), cutoff, "3")
            snapshot = storage.read_snapshot(conn, "3")
            assert snapshot.complete() == expected.complete()
            assert snapshot.relations() == expected.relations()
            assert (snapshot.log_position, snapshot.event_id) == (expected.log_position, expected.event_id)
