"""A-G9: fixed projector-2 bytes and roots, ADR 0034 §1/R1 / ADR 0025."""
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
from nyx import hashing, merkle, projection, storage
from test_event_integrity import entries
from test_reducer_boundary import decoded


def test_ag9_projector2_fixed_log_bytes_roots_and_recovery(tmp_path):
    golden = json.loads((Path(__file__).parent / "fixtures/version2_ordinary.json").read_bytes())
    log = entries("2")
    assert [[asdict(env), data] for env, data in decoded(log)] == golden["events"]
    at = golden["as_of"]
    expected = golden["expected_canonical"].encode("utf-8")
    snapshot = projection.project_snapshot(decoded(log), at, "2")
    assert hashing.canonical_json(snapshot.complete()).encode("utf-8") == expected
    assert {kind: merkle.digest(root) for kind, root in snapshot.roots.items()} == golden["expected_roots"]
    assert {bid: hashing.canonical_json(snapshot.header(bid)) for bid in snapshot.beliefs()} == golden["expected_headers"]
    with closing(storage.init_db(tmp_path / "frozen2.db", create=True)) as conn:
        for pair in log:
            storage.safe_append_event(conn, *pair, "2")
            storage.materialize_pending(conn, at, "2")
        for rebuild in (False, True):
            if rebuild:
                storage.rebuild_projection(conn, at, "2")
            assert hashing.canonical_json(storage.read_snapshot(conn, "2").complete()).encode("utf-8") == expected
            assert dict(conn.execute("SELECT kind,root_hash FROM committed_roots WHERE projector_version='2'")) == golden["expected_roots"]
            assert {bid: raw for bid, raw in conn.execute("SELECT belief_id,content FROM projected_beliefs WHERE projector_version='2'")} == golden["expected_headers"]
            assert conn.execute("SELECT log_position,event_id FROM derived_progress WHERE projector_version='2'").fetchone() == (3, "e-3")
