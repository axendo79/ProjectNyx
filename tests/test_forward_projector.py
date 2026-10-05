"""ADR 0034 section 1a: complete semantic equality and explicit dispatch."""
from contextlib import closing
from copy import deepcopy

import pytest

from nyx import projection, storage
from test_event_integrity import entries
from test_reducer_boundary import T2, decoded


def test_cross_version_equivalence():
    from nyx import forward
    log = decoded(entries("2")[:2])
    old = projection.project_snapshot(log, T2, "2")
    new = projection.project_snapshot(log, T2, "3")
    forward.assert_semantically_equivalent(old, new)
    assert new.projector_version == "3"
    forward.verify_lineage(log, T2)
    for field, value in (("value", "tampered"), ("live_status", "expired")):
        altered = deepcopy(new.complete())
        altered["claim_candidates"]["c-a"][field] = value
        with pytest.raises(ValueError):
            forward.assert_semantically_equivalent_values(old.complete(), altered)
    altered = deepcopy(new.complete())
    altered["events"][log[1][0].event_id]["payload"]["view_version_hash"] = "must compare payload"
    with pytest.raises(ValueError):
        forward.assert_semantically_equivalent_values(old.complete(), altered)


def test_registered_storage_and_refusals(tmp_path):
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in entries("2"):
            storage.safe_append_event(conn, *pair, "3")
            storage.materialize_pending(conn, T2, "3")
        assert storage.read_snapshot(conn, "3").complete() == projection.project_snapshot(
            storage.read_all_events(conn), T2, "3").complete()
        assert storage.read_claim_candidate(conn, "c-a", "3")["live_status"] == "live"
        storage.rebuild_projection(conn, T2, "3")
        with conn:
            conn.execute("DROP TABLE candidate_relations")
            conn.execute("UPDATE schema_meta SET version=4")
        before = tuple(conn.iterdump())
        for action in (lambda: storage.read_snapshot(conn, "3"),
                       lambda: storage.evaluate_whole_view(conn, T2, "3"),
                       lambda: storage.rebuild_projection(conn, T2, "3")):
            with pytest.raises(storage.SchemaCompatibilityError):
                action()
            assert tuple(conn.iterdump()) == before
    for projector_version in (None, "unknown"):
        with pytest.raises(ValueError):
            projection.project_snapshot([], T2, projector_version)
    with pytest.raises(TypeError):
        projection.project_snapshot([], T2)
