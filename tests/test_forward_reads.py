"""Live/retained read shapes and atomic relation publication/recovery."""
from contextlib import closing
import sqlite3
import json
import pytest
from nyx import events, projection, storage
from test_forward_correction import append, correction
from test_forward_expiry import expiry
from test_forward_replacement import replacement, simple_log
from test_reducer_boundary import T2, decoded, event


def transition_log():
    log = simple_log()
    log.append(event(events.CANDIDATE_REPLACED, replacement(["c-a"]), 3, log[-1]))
    log.append(event(events.CORRECTION_APPENDED, correction(["c-next"], "c-final"), 4, log[-1]))
    log.append(event(events.CANDIDATE_EXPIRED, expiry(["c-final"]), 5, log[-1]))
    return log


def test_reads_and_every_prefix(tmp_path):
    log = transition_log()
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pos, pair in enumerate(log, 1):
            append(conn, pair)
            snapshot = projection.project_snapshot(decoded(log), pair[0].recorded_at, "3")
            assert storage.read_snapshot(conn, "3").complete() == projection.project_snapshot(
                decoded(log[:pos]), T2, "3").complete()
            sets = storage.read_candidate_sets(conn, "b-a", "3")
            assert sets == snapshot.candidate_sets("b-a")
            if pos >= 2:
                assert len(sets["live"]) == (0 if pos == 5 else 1)
                assert len(sets["retained"]) == max(0, pos - 2)
                for item in sets["retained"]:
                    cid = item["candidate"]["claim_candidate_id"]
                    assert storage.read_claim_candidate_details(conn, cid, "3") == item
                    ending = item["ending_relation"]
                    assert ending["event_id"] in item["candidate"]["superseding_events"]
                    assert ending["log_position"] <= pos
            if pos >= 3:
                with pytest.raises(ValueError): storage.read_belief_scalar(conn, "b-a", "3")
        assert storage.read_candidate_sets(conn, "absent", "3") is None
        assert storage.read_claim_candidate_details(conn, "absent", "3") is None
        rows = conn.execute("SELECT target_candidate_id,event_id,relation,log_position FROM candidate_relations ORDER BY log_position").fetchall()
        assert rows == [("c-a", "e-3", "replaced_by", 3), ("c-next", "e-4", "corrected_by", 4),
                        ("c-final", "e-5", "expired_at", 5)]
        storage.rebuild_projection(conn, log[1][0].recorded_at, "3")
        assert not storage.read_candidate_sets(conn, "b-a", "3")["retained"]
        assert conn.execute("SELECT count(*) FROM candidate_relations").fetchone() == (0,)


@pytest.mark.parametrize("table", [None, "candidate_relations", "derived_progress", "committed_nodes",
                                    "committed_roots", "projected_beliefs"])
def test_append_and_publication_crash_recovers(tmp_path, table):
    log = transition_log()[:3]
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in log[:2]: append(conn, pair)
        storage.safe_append_event(conn, *log[2], "3")
        # Layer A survives; until publication the previous atomic prefix remains.
        before = storage.read_snapshot(conn, "3").complete()
        if table:
            with conn:
                conn.execute(f"CREATE TRIGGER crash BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'crash'); END")
            with pytest.raises(sqlite3.DatabaseError): storage.materialize_pending(conn, T2, "3")
            assert storage.read_snapshot(conn, "3").complete() == before
            assert conn.execute("SELECT count(*) FROM candidate_relations").fetchone() == (0,)
            assert conn.execute("SELECT log_position FROM derived_progress WHERE projector_version='3'").fetchone() == (2,)
            with conn: conn.execute("DROP TRIGGER crash")
        storage.rebuild_projection(conn, T2, "3")
        assert storage.read_snapshot(conn, "3").complete() == projection.project_snapshot(decoded(log), T2, "3").complete()
        assert storage.read_candidate_sets(conn, "b-a", "3")["retained"][0]["ending_relation"] == {
            "target_candidate_id": "c-a", "event_id": "e-3", "relation": "replaced_by", "log_position": 3}


@pytest.mark.parametrize("damage", ["deleted", "relation", "position", "extra"])
def test_relation_reads_refuse_corruption(tmp_path, damage):
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in transition_log()[:3]: append(conn, pair)
        with conn:
            if damage == "deleted": conn.execute("DELETE FROM candidate_relations")
            elif damage == "relation": conn.execute("UPDATE candidate_relations SET relation='expired_at'")
            elif damage == "position": conn.execute("UPDATE candidate_relations SET log_position=2")
            else: conn.execute("INSERT INTO candidate_relations VALUES ('3','c-next','e-3','expired_at',3)")
        with pytest.raises(ValueError, match="relation"):
            storage.read_candidate_sets(conn, "b-a", "3")


def test_selected_forward_freshness_and_frozen_inventory(tmp_path):
    log = simple_log()
    with closing(storage.init_db(tmp_path / "store.db", create=True)) as conn:
        for pair in log:
            storage.safe_append_event(conn, *pair, "2")
            storage.materialize_pending(conn, T2, "2")
        assert storage.read_store_metadata(conn)["projector_versions"] == ["1", "2"]
        storage.materialize_pending(conn, T2, "3")
        assert storage.read_belief_status(conn, "b-a", "3")["stale"] is False
        extra = event(events.OBSERVATION_RECORDED, {"claims": [
            {**decoded(log)[1][1]["claims"][0], "claim_candidate_id": "ordinary-later"}]}, 3, log[-1])
        storage.safe_append_event(conn, *extra, "2")
        assert storage.read_belief_status(conn, "b-a", "3")["stale"] is True
        assert storage.read_entity_status(conn, "s-a", "3")["stale"] is True


def test_cli_live_and_retained_at_cutoff(tmp_path, capsys):
    from nyx import cli
    path = tmp_path / "store.db"
    log = transition_log()
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log: append(conn, pair)
    assert cli.main(["belief", "b-a", "--db", str(path), "--projector", "3", "--json"]) == 0
    current = json.loads(capsys.readouterr().out)
    assert current["candidate_sets"]["live"] == []
    assert len(current["candidate_sets"]["retained"]) == 3
    assert cli.main(["belief", "b-a", "--db", str(path), "--projector", "3", "--json",
                     "--as-of", log[1][0].recorded_at]) == 0
    earlier = json.loads(capsys.readouterr().out)
    assert not earlier["candidate_sets"]["retained"]
    assert earlier["candidate_sets"]["live"][0]["value"] == "4100"


def test_committed_selectors_do_not_fall_back():
    from nyx import committed_storage
    for call in (lambda: committed_storage.read_snapshot_for(object(), "unknown"),
                 lambda: committed_storage.publish_for(object(), object(), "unknown")):
        with pytest.raises(ValueError, match="projector"):
            call()
