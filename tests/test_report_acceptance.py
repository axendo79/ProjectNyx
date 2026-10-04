"""ADR 0031 first-slice finish line, using only pinned reviewed public inputs."""
from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import pytest

from nyx import ingestion, integrity, projection, report_backup, report_importer as importer, reports, storage, writer
from nyx.report_policy import ReportPolicyError, git
from test_report_admission import AS_OF, deployment, mention, observation, source, tip
from test_report_importer import OLDER, PATH, REVISION
from test_report_policy import REPOSITORY, ROOT, policy_files


@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_slice_one_finish_line(tmp_path, monkeypatch, projector_version):
    d = deployment(tmp_path)
    paths = sorted(a[2] for a in d.policy.artifacts if a[:2] == (REPOSITORY, REVISION))
    release = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    with closing(d.open_writer(create=True)) as conn:
        importer.prepare_import(conn, REPOSITORY, REVISION, paths, 'public', projector_version=projector_version)
        first = importer.resume_import(conn, 'public', projector_version=projector_version)
        assert first['publication']['log_position'] == tip(conn)[0]
        all_reports = reports.read_report_details(conn, first['claim_candidate_ids'], projector_version=projector_version)
        assert {r['artifact']['path'] for r in all_reports['reports']} == set(paths)
        one = next(r for r in all_reports['reports'] if r['artifact']['path'] == PATH and r['property_id'] == 'adr.status.literal')
        raw = importer.read_artifacts(d.policy, REPOSITORY, REVISION, [PATH])[0]
        assert one['artifact'] == raw.descriptor
        span = one['provenance']['location']
        assert raw.data[span['start_byte']:span['end_byte']].decode('utf-8') == one['value']
        assert one['report_scope']['meaning'] == 'artifact_at_revision_stated'
        importer.prepare_import(conn, REPOSITORY, OLDER, [PATH], 'older', projector_version=projector_version)
        second = importer.resume_import(conn, 'older', projector_version=projector_version)
        older_status = next(c for c in second['claim_candidate_ids'] if storage.read_claim_candidate(conn, c, projector_version)['property_id'] == 'adr.status.literal')
        paired = reports.read_report_details(conn, [one['claim_candidate_id'], older_status], projector_version=projector_version)
        assert len({r['value'] for r in paired['reports']}) == 2
        assert len({r['belief_id'] for r in paired['reports']}) == 1
        assert all('head' not in r and 'winner' not in r for r in paired['reports'])
        # A new run is saved in full, then loses acknowledgment after Layer A append.
        importer.prepare_import(conn, REPOSITORY, OLDER, [PATH], 'interrupted', projector_version=projector_version)
        saved_path = importer.manifest_path(conn, 'interrupted')
        saved_bytes = saved_path.read_bytes()
        submit = ingestion.submit
        def lose_ack(conn, pair, as_of, projector_version):
            storage.append_submission(conn, pair, projector_version)
            raise RuntimeError('lost acknowledgment before publication')
        monkeypatch.setattr(ingestion, 'submit', lose_ack)
        with pytest.raises(RuntimeError): importer.resume_import(conn, 'interrupted', projector_version=projector_version)
        monkeypatch.setattr(ingestion, 'submit', submit)
        committed_tip = tip(conn)
        importer.resume_import(conn, 'interrupted', projector_version=projector_version)
        assert tip(conn) == committed_tip
        assert saved_path.read_bytes() == saved_bytes
        # Replay at the same final evaluation time covers IDs, source, hashes and roots.
        shared_as_of = writer.clock_now()
        storage.rebuild_projection(conn, shared_as_of, projector_version)
        assert storage.read_snapshot(conn, projector_version).complete() == projection.project_snapshot(
            storage.read_all_events(conn), shared_as_of, projector_version).complete()
        before = tip(conn)
        for run in ('public', 'older', 'interrupted'): importer.resume_import(conn, run, projector_version=projector_version)
        assert tip(conn) == before
        bundle = report_backup.backup_bundle(conn, tmp_path / 'bundle', projector_version=projector_version,
            software_revision=release, policy_revision=release)
    restored = report_backup.restore_bundle(bundle, tmp_path / 'restored.db', repositories={REPOSITORY: ROOT}, projector_version=projector_version)
    with closing(restored.open_writer()) as conn:
        assert tip(conn) == before
        final = importer.resume_import(conn, 'public', projector_version=projector_version)
        assert final['publication'] == {'log_position': before[0], 'stale': False}
        assert tip(conn) == before
        assert importer.manifest_path(conn, 'interrupted').read_bytes() == saved_bytes
        assert len(reports.read_report_details(conn, [one['claim_candidate_id'], older_status], projector_version=projector_version)['reports']) == 2
        assert all(c['property_id'] in reports.PROPERTIES for c in storage.read_snapshot(conn, projector_version).records('claim_candidates').values())


def test_saved_uncommitted_requests_retirement_refuses_without_repair(tmp_path):
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        file = importer.prepare_import(conn, REPOSITORY, REVISION, [PATH], 'uncommitted', projector_version='2')
        saved = file.read_bytes()
        assert tip(conn) == (0, None)
    (config / 'report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')
    retired = deployment(tmp_path, config)
    with closing(retired.open_writer()) as conn:
        with pytest.raises(ReportPolicyError): importer.resume_import(conn, 'uncommitted', projector_version='2')
        assert tip(conn) == (0, None)
        assert file.read_bytes() == saved


def test_correct_caller_definition_hash_never_supplies_reviewed_trust(tmp_path):
    from nyx.report_policy import definition_digest
    d = deployment(tmp_path)
    definition = json.loads(next((ROOT / 'config/report-vocabularies/sha256').glob('*.json')).read_bytes())
    definition['identity'] = 'caller-invented'
    digest = definition_digest(definition)
    supplied = source(d.policy)
    supplied['config']['report_vocabulary'].update(identity=definition['identity'], definition_digest=digest)
    with closing(d.open_writer(create=True)) as conn:
        before = tip(conn)
        with pytest.raises(ReportPolicyError):
            storage.append_submission(conn, mention(conn, d.policy, supplied), '2')
        assert tip(conn) == before


@pytest.mark.parametrize('event_kind', ['mention', 'observation'])
def test_config_only_vocabulary_collision_precedes_retirement(tmp_path, event_kind):
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        m = mention(conn, d.policy)
        committed_m = ingestion.submit(conn, m, AS_OF, '2')
        o = observation(conn, d.policy)
        committed_o = ingestion.submit(conn, o, AS_OF, '2')
    (config / 'report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')
    with closing(deployment(tmp_path, config).open_writer()) as conn:
        retained, committed = (m, committed_m) if event_kind == 'mention' else (o, committed_o)
        before = tip(conn)
        changed = json.loads(retained[0].source)
        changed['config']['report_vocabulary']['version'] = 'invented'
        conflict = replace(retained[0], source=json.dumps(changed)), retained[1]
        with pytest.raises(integrity.IntegrityError): ingestion.submit(conn, conflict, AS_OF, '2')
        assert ingestion.submit(conn, retained, AS_OF, '2') == committed
        assert tip(conn) == before
