"""Frozen R092 TEST evidence. Routine cases use no Git or live rename heuristic."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))

import pytest

from nyx import hashing, integrity, storage
from test_report_policy import ROOT, REPOSITORY

FIXTURE = ROOT / 'tests/fixtures/adr_reports/902467a-r092'


def frozen_inputs():
    capture = json.loads((FIXTURE / 'capture.json').read_bytes())
    from nyx.report_importer import Artifact
    artifacts = [Artifact(REPOSITORY, info['revision'], info['path'], info['blob'], (FIXTURE / name).read_bytes())
                 for name, info in capture['artifacts'].items()]
    return capture, artifacts


def test_exact_frozen_capture_native_objects_and_transcript():
    capture, artifacts = frozen_inputs()
    assert capture['git_version'] == '2.53.0.windows.2'
    assert capture['parent'] == '823b3ab776faf2635f37c8c3bcdd645c3850f784'
    assert capture['commit'] == '902467afa54887de0d15ab9f1a9d23403e9628cc'
    transcript = (FIXTURE / 'rename-report.bin').read_bytes()
    assert transcript == b'R092\0decisions/0009-projection-parameters.md\0decisions/0010-projection-parameters.md\0'
    assert hashlib.sha256(transcript).hexdigest() == capture['transcript_sha256']
    assert capture['independent_tree_checks']['passed'] is True
    assert capture['command'][1:7] == ['-c', 'diff.renames=true', '-c', 'diff.renameLimit=0', '-c', 'core.quotePath=false']
    for artifact in artifacts:
        assert hashlib.sha1(b'blob ' + str(len(artifact.data)).encode() + b'\0' + artifact.data).hexdigest() == artifact.blob
    assert {a.blob for a in artifacts} == {'67e7f46e0cd558b64cebfea6af4ffda4fbb4cb81',
        'fe8f2699577a910206e558dfb8607a362db841a3', 'a495d359f6f7fff2b1edcba09b9a32044aab27b6'}


@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_frozen_rename_later_python_no_number_aliasing_or_git_claim(tmp_path, monkeypatch, projector_version):
    capture, artifacts = frozen_inputs()
    from nyx import report_importer as importer, reports, report_policy
    # Trusted TEST construction from frozen, reviewed tree facts. Startup's real
    # Git expansion is tested separately; this routine fixture performs no Git I/O.
    definitions, admitted, originals = {}, set(), {}
    root = ROOT / 'config'
    for file in root.rglob('*.json'):
        originals[file.relative_to(root).as_posix()] = file.read_bytes()
    for name, raw in originals.items():
        if name.startswith('report-vocabularies/'):
            definition = report_policy.validate_definition(report_policy.strict_json(raw, name), name)
            digest = report_policy.definition_digest(definition)
            key = (definition['identity'], definition['version'], 'sha256', 'nyx.canonical-json/1', digest)
            definitions[key] = definition
    for decl in json.loads(originals['report-admission.json'])['admitted']:
        admitted.add(report_policy.declaration(decl, 'TEST admission'))
    reviewed = json.loads(originals['public-report-inputs.json'])['artifacts']
    for artifact in artifacts:
        assert any(artifact.repository == r['repository'] and artifact.revision == r['revision']
                   and artifact.path.startswith(r['path_prefix']) for r in reviewed)
    policy = report_policy.PolicySnapshot(report_policy.freeze(definitions), frozenset(admitted),
        frozenset(a.binding for a in artifacts), report_policy.freeze(originals), report_policy.freeze({}))
    monkeypatch.setattr(report_policy, 'git', lambda *a, **kw: pytest.fail('routine frozen fixture called Git'))
    with closing(storage.init_db(tmp_path / 'fixture.db', create=True, report_policy=policy)) as conn:
        previous = []
        for index, artifact in enumerate(artifacts):
            run = f'artifact-{index}'
            importer.prepare_artifacts(conn, [artifact], run, projector_version=projector_version)
            complete = importer.resume_import(conn, run, projector_version=projector_version)
            previous.extend(complete['claim_candidate_ids'])
        details = reports.read_report_details(conn, previous, projector_version=projector_version)['reports']
        subjects = {r['artifact']['path']: r['subject_id'] for r in details}
        assert len(subjects) == len(set(subjects.values())) == 3
        assert set(subjects) == {'decisions/0009-projection-parameters.md',
            'decisions/0010-projection-parameters.md', 'decisions/0009-python-314-re-adopted-as-target.md'}
        assert len(details) == len(previous)
        assert all(r['property_id'] in reports.PROPERTIES and r['artifact']['kind'] == 'adr-path' for r in details)
        snapshot = storage.read_snapshot(conn, projector_version)
        assert len(snapshot.records('entities')) == len(snapshot.records('mentions')) == 3
        assert all(c['property_id'] != 'git.rename.report' for c in snapshot.records('claim_candidates').values())
