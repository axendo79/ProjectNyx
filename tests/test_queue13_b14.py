"""B14: mixed working-copy lifecycle, ADR 0034 §§1a,10 / 0035 §1 / 0031 backup."""
from contextlib import closing
from pathlib import Path
from nyx import committed, forward, projection, report_backup, report_importer, report_policy, storage
from queue13_helpers import payload
from test_reducer_boundary import claim, event, mention
from test_report_admission import AS_OF, deployment
from test_report_importer import PATH, REVISION
from test_report_policy import REPOSITORY, ROOT
from test_store_transition import tool
from test_verify_store import verifier


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_b14_mixed_store_tied_prefixes_manifests_and_restore(tmp_path):
    d = deployment(tmp_path)
    repositories = {REPOSITORY: ROOT}
    revision = report_policy.git(ROOT, "rev-parse", "HEAD").decode().strip()
    with closing(d.open_writer(create=True, clock=lambda: AS_OF)) as conn:
        manifest = report_importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], "saved", projector_version="2")
        report_importer.resume_import(conn, "saved", projector_version="2")
        saved = manifest.read_bytes()
    # Ordinary producer on a disposable unbound writer; this is persistence /
    # replay coverage, not a claim that report-only admission permits this writer.
    with closing(storage.init_db(d.store)) as conn:
        previous = storage.last_event_hash(conn)
        first = event("entity_mention_recorded", mention(), 3, recorded_at=AS_OF, prev_event_hash=previous)
        second = event("observation_recorded", {"claims": [claim("ordinary")]}, 4, first,
                       recorded_at="2026-10-05T08:00:00-04:00")
        for pair in (first, second):
            storage.safe_append_event(conn, *pair, "2")
            storage.materialize_pending(conn, AS_OF, "2")
        original_log = storage.read_all_events(conn)
    with closing(d.open_writer()) as conn:
        bundle = report_backup.backup_bundle(conn, tmp_path / "source-bundle", projector_version="2",
                                             software_revision=revision, policy_revision=revision)
    source_bytes = d.store.read_bytes()
    bundle_bytes = tree(bundle)
    working = tmp_path / "working.db"
    result = tool().transition_store(d.store, working, "3", report_bundle=bundle, repositories=repositories)
    at = result["as_of"]  # Identical evaluation spelling, not only equal instants.
    assert result["positions_verified"] == 4
    assert d.store.read_bytes() == source_bytes and tree(bundle) == bundle_bytes
    assert (Path(str(working) + ".imports") / "saved/requests.json").read_bytes() == saved
    with closing(storage.init_db(working)) as conn:
        snapshot = storage.read_snapshot(conn, "3")
        reports = {cid: c for cid, c in snapshot.records("claim_candidates").items() if cid != "ordinary"}
        log = [first, second]
        for kind, target, fresh in [("candidate_replaced", "ordinary", "replacement"),
                                    ("correction_appended", "replacement", "correction"),
                                    ("candidate_expired", "correction", "unused")]:
            pair = event(kind, payload(kind, [target], fresh), snapshot.log_position + 1, log[-1],
                         recorded_at=AS_OF)
            storage.safe_append_event(conn, *pair, "3")
            storage.materialize_pending(conn, at, "3")
            log.append(pair)
            snapshot = storage.read_snapshot(conn, "3")
            assert {cid: snapshot.record("claim_candidates", cid) for cid in reports} == reports
            recorded = storage.read_all_events(conn)
            replay = projection.project_snapshot(recorded, at, "3")
            assert snapshot.complete() == replay.complete()
            assert (snapshot.log_position, snapshot.event_id) == (len(recorded), recorded[-1][0].event_id)
            assert snapshot.relations() == replay.relations()
            for bid, belief in snapshot.beliefs().items():
                assert committed.full_result_roots(belief) == snapshot.header(bid)["collection_roots"]
                assert storage.read_candidate_sets(conn, bid, "3") == replay.candidate_sets(bid)
            forward.verify_lineage(recorded, at)
            assert verifier["verify_store"](working, "3")["ok"]
        complete = snapshot.complete()
        relations = snapshot.relations()
        sets = snapshot.candidate_sets("b-a")
        assert not sets["live"] and len(sets["retained"]) == 3
        assert storage.read_all_events(conn)[:4] == original_log
    # The existing report-bundle contract explicitly selects 2. SQLite backup
    # retains all version-3 rows as well; no report producer is upgraded to 3.
    working_deployment = report_policy.ReportDeployment(working, ROOT / "config", repositories=repositories)
    with closing(working_deployment.open_writer()) as conn:
        final_bundle = report_backup.backup_bundle(conn, tmp_path / "working-bundle", projector_version="2",
                                                   software_revision=revision, policy_revision=revision)
    captured = tree(final_bundle)
    restored = report_backup.restore_bundle(final_bundle, tmp_path / "restored.db", repositories=repositories,
                                           projector_version="2")
    with closing(storage.open_readonly(restored.store)) as conn:
        snapshot = storage.read_snapshot(conn, "3")
        assert snapshot.complete() == complete
        assert snapshot.relations() == relations and snapshot.candidate_sets("b-a") == sets
        assert verifier["verify_store"](restored.store, "3")["ok"]
    # Restore reads the bundle through SQLite; remove no files or rows to hide a change.
    assert tree(final_bundle) == captured
    assert (Path(str(restored.store) + ".imports") / "saved/requests.json").read_bytes() == saved
    assert d.store.read_bytes() == source_bytes and tree(bundle) == bundle_bytes
