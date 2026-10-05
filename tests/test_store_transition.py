"""ADR 0034 section 10 steps 1-3, exclusively temporary fixture stores."""
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import pytest
from nyx import events, forward, ingestion, projection, storage
from test_committed_schema_amendment import schema_four
from test_forward_expiry import expiry
from test_forward_retries import request
from test_reducer_boundary import T2
from test_verify_store import verifier
from test_event_integrity import entries


def tool():
    path = Path(__file__).resolve().parents[1] / 'scripts/transition_store.py'
    spec = importlib.util.spec_from_file_location('transition_store', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('schema', [4, 5])
def test_source_unchanged_every_position_proof_and_backup_restore(tmp_path, schema):
    source, working = tmp_path / 'source.db', tmp_path / 'working.db'
    schema_four(source)
    if schema == 5:
        old = tmp_path / 'old.db'
        with closing(storage.open_readonly(source)) as conn, closing(sqlite3.connect(old)) as dest:
            conn.backup(dest)
        storage.migrate_working_copy(old, source)
    before = source.read_bytes()
    with closing(storage.open_readonly(source)) as conn:
        log = storage.read_all_events(conn)
        frozen = storage.read_snapshot(conn, '2').complete()
    result = tool().transition_store(source, working, '3')
    assert result['positions_verified'] == len(log)
    assert len(result['source_sha256']) == 64
    assert source.read_bytes() == before
    assert Path(result['backup']).is_file()
    assert working.with_name(working.name + '.transition.json').is_file()
    with closing(storage.open_readonly(working)) as conn:
        assert conn.execute('SELECT version FROM schema_meta').fetchone() == (5,)
        assert storage.read_all_events(conn) == log
        assert storage.read_snapshot(conn, '2').complete() == frozen
        forward.assert_semantically_equivalent(projection.project_snapshot(log, result['as_of'], '2'),
                                               storage.read_snapshot(conn, '3'))
    with closing(storage.init_db(working, clock=lambda: T2)) as conn:
        ingestion.submit(conn, request(events.CANDIDATE_EXPIRED, expiry(['c-a']), 'working-expiry'), T2, '3')
        sets = storage.read_candidate_sets(conn, 'b-a', '3')
        restored = tmp_path / 'restored.db'
        with closing(sqlite3.connect(restored)) as dest:
            conn.backup(dest)
    with closing(storage.open_readonly(restored)) as conn:
        assert storage.read_candidate_sets(conn, 'b-a', '3') == sets
    assert verifier['verify_store'](restored, '3')['ok']
    assert source.read_bytes() == before


def test_refuses_source_as_output_and_existing_outputs(tmp_path):
    source = tmp_path / 'source.db'
    schema_four(source)
    before = source.read_bytes()
    with pytest.raises(ValueError, match='distinct|new'):
        tool().transition_store(source, source, '3')
    working = tmp_path / 'working.db'
    working.write_bytes(b'keep')
    with pytest.raises(ValueError, match='new|exist'):
        tool().transition_store(source, working, '3')
    assert working.read_bytes() == b'keep'
    assert source.read_bytes() == before
    with pytest.raises(ValueError, match='projector'):
        tool().transition_store(source, tmp_path / 'other.db', '2')


def test_must_equal_mutation_fails_prefix_proof_without_source_write(tmp_path, monkeypatch):
    source = tmp_path / 'source.db'
    schema_four(source)
    before = source.read_bytes()
    original = forward.Projector.reduce
    def changed(self, snapshot, envelope, payload, as_of):
        delta = original(self, snapshot, envelope, payload, as_of)
        if delta.entities:
            delta.entities['s-a']['subject_id'] = 'reminted'
            return forward.committed._finish(snapshot, delta, {})
        return delta
    monkeypatch.setattr(forward.Projector, 'reduce', changed)
    with pytest.raises(ValueError, match='equivalence'):
        tool().transition_store(source, tmp_path / 'working.db', '3')
    assert source.read_bytes() == before


@pytest.mark.parametrize('populated', [False, True])
def test_empty_and_wal_resident_sources_are_copied_without_source_mutation(tmp_path, populated):
    source, working = tmp_path / 'source.db', tmp_path / 'working.db'
    with closing(storage.init_db(source, create=True, clock=lambda: T2)) as conn:
        if populated:
            for pair in entries('2'):
                storage.safe_append_event(conn, *pair, '2')
                storage.materialize_pending(conn, T2, '2')
        before = source.read_bytes()
        wal = source.with_name(source.name + '-wal')
        before_wal = wal.read_bytes()
        log = storage.read_all_events(conn)
        result = tool().transition_store(source, working, '3')
        assert result['positions_verified'] == len(log)
        assert source.read_bytes() == before
        assert wal.read_bytes() == before_wal
        with closing(storage.open_readonly(result['backup'])) as backup:
            assert storage.read_all_events(backup) == log
        with closing(storage.open_readonly(working)) as copy:
            assert storage.read_all_events(copy) == log
            assert storage.read_snapshot(copy, '3').log_position == len(log)
        assert verifier['verify_store'](working, '3')['ok']


def test_cli_requires_explicit_projector_and_reports_proof(tmp_path, capsys):
    source, working = tmp_path / 'source.db', tmp_path / 'working.db'
    schema_four(source)
    module = tool()
    with pytest.raises(SystemExit) as failure:
        module.main(['--source', str(source), '--working', str(working)])
    assert failure.value.code == 2
    assert not working.exists()
    assert module.main(['--source', str(source), '--working', str(working),
                        '--projector-version', '3']) == 0
    import json
    assert json.loads(capsys.readouterr().out)['identities_unchanged'] is True


def test_retained_import_manifests_require_a_report_bundle(tmp_path):
    # ADR 0031: <store>.imports/<run-id>/requests.json is durable data that
    # travels with backups; the working copy and source backup keep exact copies.
    source, working = tmp_path / 'source.db', tmp_path / 'working.db'
    schema_four(source)
    manifest = source.with_name(source.name + '.imports') / 'run-1' / 'requests.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b'{"format": "nyx.adr-import-requests/1"}\n')
    before = manifest.read_bytes()
    with pytest.raises(ValueError, match='report bundle'):
        tool().transition_store(source, working, '3')
    assert manifest.read_bytes() == before
    assert not working.exists()


def test_transition_without_imports_records_none_and_refuses_existing_output(tmp_path):
    source, working = tmp_path / 'source.db', tmp_path / 'working.db'
    schema_four(source)
    working.with_name(working.name + '.imports').mkdir()
    with pytest.raises(ValueError, match='already exists'):
        tool().transition_store(source, working, '3')
    other = tmp_path / 'other.db'
    assert tool().transition_store(source, other, '3')['imports'] == {}
    assert not other.with_name(other.name + '.imports').exists()


def repositories():
    from test_report_policy import REPOSITORY, ROOT
    return {REPOSITORY: ROOT}


def interrupted_report_store(tmp_path, boundary='mention'):
    """A real ADR 0031 store, interrupted at a supported boundary, plus its bundle."""
    from nyx import report_importer as importer, report_backup, report_policy
    from test_report_admission import AS_OF, deployment
    from test_report_importer import PATH, REVISION
    from test_report_policy import REPOSITORY, ROOT, policy_files
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        manifest = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        mention_request, _ = importer.requests(importer.read_manifest(manifest, projector_version='2'))
        if boundary == 'mention':
            ingestion.submit(conn, mention_request, AS_OF, '2')
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version='2',
                                             software_revision=revision, policy_revision=revision)
    return d, config, bundle


@pytest.mark.parametrize('boundary', ['before-append', 'mention'])
def test_report_store_transition_requires_its_bundle_and_resumes_on_working_copy(tmp_path, boundary):
    # ADR 0031 BACKUP BUNDLE row and ADR 0034 section 10 step 1: a report store's
    # backup is its ADR 0031 bundle (policy, definitions, revisions, manifests).
    from nyx import report_importer as importer, reports
    from nyx.report_policy import ReportDeployment
    from test_report_policy import REPOSITORY, ROOT
    d, config, bundle = interrupted_report_store(tmp_path, boundary)
    with pytest.raises(ValueError, match='report bundle'):
        tool().transition_store(d.store, tmp_path / 'unbundled.db', '3')
    with closing(storage.open_readonly(d.store)) as conn:
        source_tip = storage.last_event_hash(conn)
    working = tmp_path / 'working.db'
    result = tool().transition_store(d.store, working, '3', report_bundle=bundle,
                                     repositories=repositories())
    assert result['report_bundle']['tip_hash'] == source_tip
    assert result['report_bundle']['projector_version'] == '2'
    assert len(result['report_bundle']['bundle_sha256']) == 64
    resumed = ReportDeployment(working, config, repositories={REPOSITORY: ROOT})
    with closing(resumed.open_writer()) as conn:
        count = conn.execute('SELECT count(*) FROM events').fetchone()[0]
        out = importer.resume_import(conn, 'one', projector_version='2')
        assert conn.execute('SELECT count(*) FROM events').fetchone()[0] == 2
        assert count == (0 if boundary == 'before-append' else 1)
        details = reports.read_report_details(conn, out['claim_candidate_ids'], projector_version='2')
        assert len(details['reports']) == 3
        tip_after = storage.last_event_hash(conn)
        importer.resume_import(conn, 'one', projector_version='2')
        assert storage.last_event_hash(conn) == tip_after
    # Reading the bundle during transition left it intact and restorable.
    from nyx import report_backup
    report_backup.restore_bundle(bundle, tmp_path / 'restored.db', repositories={REPOSITORY: ROOT},
                                 projector_version='2')


def test_report_store_transition_refuses_a_stale_bundle(tmp_path):
    from nyx import report_importer as importer
    d, _, bundle = interrupted_report_store(tmp_path)
    with closing(d.open_writer()) as conn:
        importer.resume_import(conn, 'one', projector_version='2')
    with pytest.raises(ValueError, match='report bundle'):
        tool().transition_store(d.store, tmp_path / 'working.db', '3', report_bundle=bundle,
                                repositories=repositories())


def test_report_store_transition_refuses_an_unrestorable_bundle(tmp_path):
    # File hashes, log, tip and manifests all match, but restore_bundle would
    # reject the bindings; the transition must refuse the same bundle.
    import json
    d, _, bundle = interrupted_report_store(tmp_path)
    metadata = json.loads((bundle / 'bundle.json').read_bytes())
    metadata['vocabulary_bindings'] = []
    (bundle / 'bundle.json').write_text(json.dumps(metadata), encoding='utf-8')
    with pytest.raises(ValueError, match='report bundle'):
        tool().transition_store(d.store, tmp_path / 'working.db', '3', report_bundle=bundle,
                                repositories=repositories())
    assert not (tmp_path / 'working.db').exists()
