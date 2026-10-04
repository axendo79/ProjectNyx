"""Durable complete semantic requests and first-import completion, ADR 0031."""
from contextlib import closing
import json
from pathlib import Path

import pytest

from nyx import ingestion, storage
from test_report_admission import AS_OF, deployment, tip
from test_report_policy import REPOSITORY, ROOT

REVISION = '34ec397e7eaa5daf10ffbff4c4f5b5021d4fed40'
OLDER = '98dc48d395a0945cf0c3d728c706e429db3ada97'
PATH = 'decisions/0031-source-report-claims.md'


@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_interrupted_import_resume_complete_and_no_append_retry(tmp_path, monkeypatch, projector_version):
    from nyx import report_importer as importer
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        path = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'first', projector_version=projector_version)
        saved = path.read_bytes()
        manifest = json.loads(saved)
        assert set(manifest) == {'format', 'projector_version', 'associations', 'requests'}
        assert len(manifest['requests']) == 2
        assert tip(conn)[0] == 0
        original_submit = ingestion.submit
        count = 0
        def interrupted(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2: raise RuntimeError('crash after mention')
            return original_submit(*args, **kwargs)
        monkeypatch.setattr(ingestion, 'submit', interrupted)
        with pytest.raises(RuntimeError): importer.resume_import(conn, 'first', projector_version=projector_version)
        assert tip(conn)[0] == 1
        monkeypatch.setattr(ingestion, 'submit', original_submit)
    with closing(d.open_writer()) as conn:
        result = importer.resume_import(conn, 'first', projector_version=projector_version)
        assert result['publication'] == {'log_position': 2, 'stale': False}
        assert len(result['claim_candidate_ids']) == 3
        before = tip(conn)
        assert importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'first', projector_version=projector_version).read_bytes() == saved
        importer.resume_import(conn, 'first', projector_version=projector_version)
        assert tip(conn) == before
        assert path.read_bytes() == saved
        assert path == Path(str(d.store) + '.imports') / 'first/requests.json'
        request_source = json.loads(manifest['requests'][1]['event_request']['source'])
        assert request_source['config']['source_dates']
        assert request_source['config']['report_artifact']['revision'] == REVISION
        assert request_source['config']['report_artifact']['path'] == PATH
        assert 'recorded_at' not in manifest['requests'][1]['event_request']
        assert 'prev_event_hash' not in manifest['requests'][1]['event_request']
        candidates = [storage.read_claim_candidate(conn, c, projector_version) for c in result['claim_candidate_ids']]
        assert len({c['occurred_at'] for c in candidates}) == 1


def test_retained_associations_later_revisions_and_no_matching(tmp_path):
    from nyx import report_importer as importer
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        one = importer.prepare_import(conn, REPOSITORY, OLDER, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
        first = json.loads(one.read_bytes())
        two = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'two', projector_version='2')
        second = json.loads(two.read_bytes())
        assert second['associations'] == first['associations']
        assert len(second['requests']) == 1
        importer.resume_import(conn, 'two', projector_version='2')
        assert tip(conn)[0] == 3
        snapshot = storage.read_snapshot(conn, '2')
        assert len(snapshot.records('mentions')) == 1
        assert len(snapshot.records('claim_candidates')) == 6
        assert len(snapshot.beliefs()) == 3
        first['associations'][0]['mention_id'] = 'missing'
        one.write_text(json.dumps(first), encoding='utf-8')
        from nyx.integrity import IntegrityError
        with pytest.raises(IntegrityError, match='association|mention'):
            importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'three', projector_version='2')


@pytest.mark.parametrize('bad', ['private-repo', 'unreviewed-revision', 'outside-prefix', 'bad-blob', 'bad-bytes', 'run-traversal'])
def test_public_artifact_and_manifest_refusal(tmp_path, bad):
    from nyx import report_importer as importer
    from nyx.report_policy import ReportPolicyError
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        if bad in ('bad-blob', 'bad-bytes'):
            artifacts = importer.read_artifacts(d.policy, REPOSITORY, REVISION, [PATH])
            a = artifacts[0]
            from dataclasses import replace
            a = replace(a, blob='0' * 40) if bad == 'bad-blob' else replace(a, data=b'# Invented')
            with pytest.raises(ReportPolicyError): importer.prepare_artifacts(conn, [a], 'bad', projector_version='2')
        else:
            repository = REPOSITORY + '/private' if bad == 'private-repo' else REPOSITORY
            revision = '0' * 40 if bad == 'unreviewed-revision' else REVISION
            paths = ['README.md'] if bad == 'outside-prefix' else [PATH]
            run = '../escape' if bad == 'run-traversal' else 'bad'
            with pytest.raises(ReportPolicyError): importer.prepare_import(conn, repository, revision, paths, run, projector_version='2')
        assert tip(conn)[0] == 0


def test_manifest_flush_failure_stops_submission_and_projector_is_required(tmp_path, monkeypatch):
    from nyx import report_importer as importer
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        with pytest.raises(TypeError): importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'absent')
        with pytest.raises(ValueError): importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'bad', projector_version='0')
        monkeypatch.setattr(importer.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('replace failed')))
        with pytest.raises(OSError): importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'failure', projector_version='2')
        assert tip(conn)[0] == 0


def test_completion_requires_publication_and_expected_claims(tmp_path):
    from nyx import report_importer as importer
    from nyx import integrity
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        path = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        manifest = importer.read_manifest(path, projector_version='2')
        for pair in importer.requests(manifest):
            storage.materialize_pending(conn, AS_OF, '2')
            storage.append_submission(conn, pair, '2')
        # A standalone store verifier can accept this pending prefix.
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from verify_store import verify_store
        assert verify_store(d.store, projector='2')['ok']
        with pytest.raises(integrity.IntegrityError, match='publication'):
            importer.check_completion(conn, manifest, projector_version='2')
        storage.materialize_pending(conn, AS_OF, '2')
        assert len(importer.check_completion(conn, manifest, projector_version='2')['claim_candidate_ids']) == 3


def test_lost_retained_manifest_refuses_instead_of_reminting(tmp_path):
    from nyx import report_importer as importer, integrity
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        path = importer.prepare_import(conn, REPOSITORY, OLDER, [PATH], 'one', projector_version='2')
        importer.resume_import(conn, 'one', projector_version='2')
        path.unlink()
        before = tip(conn)
        with pytest.raises(integrity.IntegrityError, match='retained association'):
            importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'two', projector_version='2')
        assert tip(conn) == before


def test_observation_artifact_cannot_relabel_a_different_path_subject(tmp_path):
    from nyx import report_importer as importer
    from nyx.report_policy import ReportPolicyError
    from dataclasses import replace
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        path = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'one', projector_version='2')
        manifest = importer.read_manifest(path, projector_version='2')
        m, o = importer.requests(manifest)
        ingestion.submit(conn, m, AS_OF, '2')
        a = importer.read_artifacts(d.policy, REPOSITORY, REVISION, ['decisions/0032-explicit-stage-two-projector-selection.md'])[0]
        src = json.loads(o[0].source)
        src['config']['report_artifact'] = a.descriptor
        before = tip(conn)
        with pytest.raises(ReportPolicyError):
            storage.append_submission(conn, (replace(o[0], source=json.dumps(src)), o[1]), '2')
        assert tip(conn) == before


def test_multiple_revisions_in_one_manifest_retain_planned_associations(tmp_path):
    from nyx import report_importer as importer
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        artifacts = (importer.read_artifacts(d.policy, REPOSITORY, OLDER, [PATH])
                     + importer.read_artifacts(d.policy, REPOSITORY, REVISION, [PATH]))
        file = importer.prepare_artifacts(conn, artifacts, 'together', projector_version='2')
        manifest = importer.read_manifest(file, projector_version='2')
        assert len(manifest['associations']) == 1
        result = importer.resume_import(conn, 'together', projector_version='2')
        assert result['publication']['log_position'] == 3
        assert len(result['claim_candidate_ids']) == 6
        assert len(storage.read_snapshot(conn, '2').beliefs()) == 3


def test_importer_launcher_required_projector_and_success(tmp_path):
    import subprocess
    import sys
    args = [sys.executable, '-B', str(ROOT / 'scripts/import_adr_reports.py'),
            '--store', str(tmp_path / 'cli.db'), '--config', str(ROOT / 'config'),
            '--checkout', str(ROOT), '--repository', REPOSITORY, '--revision', REVISION,
            '--path', PATH, '--run-id', 'cli', '--create']
    missing = subprocess.run(args, capture_output=True, text=True)
    assert missing.returncode == 2
    assert '--projector-version' in missing.stderr
    assert not (tmp_path / 'cli.db').exists()
    result = subprocess.run(args + ['--projector-version', '2'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['publication'] == {'log_position': 2, 'stale': False}


def test_git_object_reads_disable_implicit_lazy_fetch(monkeypatch):
    from nyx import report_policy
    from types import SimpleNamespace
    recorded = {}
    def command(args, **kwargs):
        recorded.update(kwargs)
        return SimpleNamespace(stdout=b'pinned')
    monkeypatch.setattr(report_policy.subprocess, 'run', command)
    assert report_policy.git(ROOT, 'cat-file', 'blob', 'missing') == b'pinned'
    assert recorded['env']['GIT_NO_LAZY_FETCH'] == '1'
    assert recorded['env']['GIT_TERMINAL_PROMPT'] == '0'


@pytest.mark.parametrize('binding', [None, {}, {REPOSITORY: None}, {REPOSITORY: ROOT, 'unused': 'absent-checkout'}])
def test_malformed_trusted_binding_fails_before_store(tmp_path, binding):
    from nyx.report_policy import ReportDeployment, ReportPolicyError
    with pytest.raises(ReportPolicyError):
        ReportDeployment(tmp_path / 'new.db', ROOT / 'config', repositories=binding)
    assert not (tmp_path / 'new.db').exists()
    assert not (tmp_path / 'new.db.lock').exists()
