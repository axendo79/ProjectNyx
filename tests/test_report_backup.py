"""SQLite-consistent release/manifest backup, restore, and retained retry."""
from contextlib import closing
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import pytest

from nyx import ingestion, storage, writer
from test_report_admission import AS_OF, deployment, tip
from test_report_importer import PATH, REVISION
from test_report_policy import REPOSITORY, ROOT, policy_files


@pytest.mark.parametrize('projector_version', ['1', '2'])
@pytest.mark.parametrize('boundary', ['complete', 'before-append', 'mention', 'before-publication'])
def test_backup_restore_consistent_reports_resume_and_no_reappend(tmp_path, monkeypatch, projector_version, boundary):
    from nyx import report_importer as importer, report_backup, reports, report_policy
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        manifest = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version=projector_version)
        saved = manifest.read_bytes()
        retained = importer.read_manifest(manifest, projector_version=projector_version)
        m, o = importer.requests(retained)
        if boundary == 'complete': importer.resume_import(conn, 'one', projector_version=projector_version)
        elif boundary != 'before-append':
            ingestion.submit(conn, m, AS_OF, projector_version)
            if boundary == 'before-publication': storage.append_submission(conn, o, projector_version)
        original_tip = tip(conn)
        original_status = storage.read_projection_status(conn, projector_version)
        originals = dict(d.policy.original_files)
        # Backup the loaded policy, even if deployment files changed meanwhile.
        (config / 'report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')
        original_backup = writer.WriterConnection.backup
        called = []
        def backup(self, *args, **kwargs):
            called.append(True)
            return original_backup(self, *args, **kwargs)
        monkeypatch.setattr(writer.WriterConnection, 'backup', backup)
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version=projector_version,
                                             software_revision=revision, policy_revision=revision)
        assert called == [True]
    restored = report_backup.restore_bundle(bundle, tmp_path / 'restored.db', repositories={REPOSITORY: ROOT},
                                            projector_version=projector_version)
    metadata = json.loads((bundle / 'bundle.json').read_bytes())
    assert metadata['software_revision'] == metadata['policy_revision'] == revision
    assert dict(restored.policy.original_files) == originals
    assert (Path(str(restored.store) + '.imports') / 'one/requests.json').read_bytes() == saved
    with closing(restored.open_writer()) as conn:
        assert tip(conn) == original_tip
        assert storage.read_projection_status(conn, projector_version) == original_status
        storage.read_all_events(conn)  # Consistent complete Layer A chain.
        result = importer.resume_import(conn, 'one', projector_version=projector_version)
        expected_count = 2
        assert tip(conn)[0] == expected_count
        assert result['publication'] == {'log_position': expected_count, 'stale': False}
        details = reports.read_report_details(conn, result['claim_candidate_ids'], projector_version=projector_version)
        assert len(details['reports']) == 3
        before = tip(conn)
        importer.resume_import(conn, 'one', projector_version=projector_version)
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version=projector_version)
        assert tip(conn) == before


def test_backup_retired_definitions_and_committed_requests(tmp_path):
    from nyx import report_importer as importer, report_backup, report_policy
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
    (config / 'report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')
    retired = deployment(tmp_path, config)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(retired.open_writer()) as conn:
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version='2',
            software_revision=revision, policy_revision=revision)
    restored = report_backup.restore_bundle(bundle, tmp_path / 'restored.db', repositories={REPOSITORY: ROOT}, projector_version='2')
    assert not restored.policy.admitted and restored.policy.definitions
    with closing(restored.open_writer()) as conn:
        before = tip(conn)
        importer.resume_import(conn, 'one', projector_version='2')
        assert tip(conn) == before


def test_bundle_refuses_corruption_and_existing_restore_destination(tmp_path):
    from nyx import report_importer as importer, report_backup, report_policy, integrity
    d = deployment(tmp_path)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version='2',
            software_revision=revision, policy_revision=revision)
    before = d.store.read_bytes()
    with pytest.raises(FileExistsError): report_backup.restore_bundle(bundle, d.store, repositories={REPOSITORY: ROOT}, projector_version='2')
    assert d.store.read_bytes() == before
    file = bundle / 'imports/one/requests.json'
    file.write_bytes(file.read_bytes() + b' ')
    with pytest.raises(integrity.IntegrityError):
        report_backup.restore_bundle(bundle, tmp_path / 'bad.db', repositories={REPOSITORY: ROOT}, projector_version='2')
    assert not (tmp_path / 'bad.db').exists()


def test_missing_historical_definition_refuses_restore_before_creation(tmp_path):
    from nyx import report_importer as importer, report_backup, report_policy
    from nyx.report_policy import ReportPolicyError
    import hashlib
    d = deployment(tmp_path)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version='2',
            software_revision=revision, policy_revision=revision)
    definition_file = next((bundle / 'policy/report-vocabularies/sha256').glob('*.json'))
    definition = json.loads(definition_file.read_bytes()); definition['version'] = 'retained-other'
    digest = report_policy.definition_digest(definition)
    definition_file.unlink()
    definition_file.with_name(digest + '.json').write_text(json.dumps(definition), encoding='utf-8')
    (bundle / 'policy/report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')
    metadata = json.loads((bundle / 'bundle.json').read_bytes())
    metadata['vocabulary_bindings'] = [{'identity': definition['identity'], 'version': definition['version'],
        'digest_algorithm': 'sha256', 'canonicalization_profile': 'nyx.canonical-json/1', 'definition_digest': digest}]
    metadata['files'] = {p.relative_to(bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in bundle.rglob('*') if p.is_file() and p != bundle / 'bundle.json'}
    (bundle / 'bundle.json').write_text(json.dumps(metadata), encoding='utf-8')
    with pytest.raises(ReportPolicyError):
        report_backup.restore_bundle(bundle, tmp_path / 'bad.db', repositories={REPOSITORY: ROOT}, projector_version='2')
    assert not (tmp_path / 'bad.db').exists()


def test_backup_launcher_and_restore(tmp_path):
    import subprocess
    from nyx import report_importer as importer, report_policy
    d = deployment(tmp_path)
    revision = report_policy.git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
    script = str(ROOT / 'scripts/backup_report_store.py')
    args = [sys.executable, '-B', script, 'backup', '--store', str(d.store), '--config', str(ROOT / 'config'),
            '--checkout', str(ROOT), '--repository', REPOSITORY, '--bundle', str(tmp_path / 'bundle'),
            '--software-revision', revision, '--policy-revision', revision]
    missing = subprocess.run(args, capture_output=True, text=True)
    assert missing.returncode == 2 and '--projector-version' in missing.stderr
    result = subprocess.run(args + ['--projector-version', '2'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    restored = subprocess.run([sys.executable, '-B', script, 'restore', '--store', str(tmp_path / 'restored.db'),
        '--checkout', str(ROOT), '--repository', REPOSITORY, '--bundle', str(tmp_path / 'bundle'),
        '--projector-version', '2'], capture_output=True, text=True)
    assert restored.returncode == 0, restored.stderr
