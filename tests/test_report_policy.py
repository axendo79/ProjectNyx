"""ADR 0031 policy files: trusted local startup, never replay policy."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from nyx import hashing

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/axendo79/ProjectNyx.git'
DIGEST = '73eed2df21cb3fd66388b186b397301c92bedfaadcf1b51aa822de0e1a1f8e8f'


def policy_files(tmp_path):
    target = tmp_path / 'config'
    shutil.copytree(ROOT / 'config', target)
    return target


def load(path):
    from nyx.report_policy import load_policy
    return load_policy(path, repositories={REPOSITORY: ROOT})


def test_ratified_digest_expansion_and_original_bytes():
    snapshot = load(ROOT / 'config')
    assert snapshot.declaration['definition_digest'] == DIGEST
    assert len(snapshot.definitions) == 1
    assert snapshot.original_files
    assert snapshot.artifacts == load(ROOT / 'config').artifacts
    assert any(a[2] == 'decisions/0031-source-report-claims.md' for a in snapshot.artifacts)


@pytest.mark.parametrize('bad', [
    b'{"format":"x","format":"y"}', b'\xef\xbb\xbf{}', b'\xff',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
    b'{"x":"\\ud800"}', b'{', b'{"x":1e999}',
])
def test_strict_json_refusals(tmp_path, bad):
    from nyx.report_policy import ReportPolicyError
    target = policy_files(tmp_path)
    (target / 'report-admission.json').write_bytes(bad)
    with pytest.raises(ReportPolicyError):
        load(target)


@pytest.mark.parametrize('kind', [
    'missing', 'unknown', 'duplicate-entry', 'duplicate-property', 'shape',
    'meaning', 'filename', 'binding', 'admission-extra', 'admission-duplicate',
    'unresolved', 'algorithm', 'profile', 'mutable', 'public-extra',
    'public-duplicate', 'unavailable', 'unbound', 'empty-prefix', 'wildcard',
])
def test_startup_refusals(tmp_path, kind):
    from nyx.report_policy import ReportPolicyError, definition_digest
    target = policy_files(tmp_path)
    file = next((target / 'report-vocabularies/sha256').glob('*.json'))
    definition = json.loads(file.read_bytes())
    admission = target / 'report-admission.json'
    public = target / 'public-report-inputs.json'
    a, p = json.loads(admission.read_bytes()), json.loads(public.read_bytes())
    if kind == 'missing':
        file.unlink()
    elif kind in ('unknown', 'duplicate-entry', 'duplicate-property', 'shape', 'meaning'):
        if kind == 'unknown': definition['constraints'] = {}
        if kind == 'duplicate-entry': definition['entries'].append(definition['entries'][0])
        if kind == 'duplicate-property':
            definition['entries'].append({**definition['entries'][0], 'label': 'Other'})
        if kind == 'shape': definition['entries'][0]['value_shape'] = 'git-rename-report'
        if kind == 'meaning': definition['entries'][0]['report_meaning'] = 'The world is true.'
        file.write_text(json.dumps(definition), encoding='utf-8')
    elif kind == 'filename': file.rename(file.with_name('0' * 64 + '.json'))
    elif kind == 'binding':
        definition['description'] += ' changed'
        digest = definition_digest(definition)
        file.with_name(digest + '.json').write_text(json.dumps(definition), encoding='utf-8')
    elif kind.startswith('admission-'):
        if kind.endswith('extra'): a['admitted'][0]['extra'] = True
        else: a['admitted'].append(a['admitted'][0])
    elif kind == 'unresolved': a['admitted'][0]['definition_digest'] = '0' * 64
    elif kind == 'algorithm': a['admitted'][0]['digest_algorithm'] = 'sha1'
    elif kind == 'profile': a['admitted'][0]['canonicalization_profile'] = 'other'
    elif kind == 'mutable': p['artifacts'][0]['revision'] = 'main'
    elif kind == 'public-extra': p['artifacts'][0]['path'] = 'extra'
    elif kind == 'public-duplicate': p['artifacts'].append(p['artifacts'][0])
    elif kind == 'unavailable': p['artifacts'][0]['revision'] = '0' * 40
    elif kind == 'unbound': p['artifacts'][0]['repository'] += 'unreviewed'
    elif kind == 'empty-prefix': p['artifacts'][0]['path_prefix'] = 'absent/'
    elif kind == 'wildcard': p['artifacts'][0]['path_prefix'] = 'decisions/*'
    admission.write_text(json.dumps(a), encoding='utf-8')
    public.write_text(json.dumps(p), encoding='utf-8')
    with pytest.raises(ReportPolicyError): load(target)


def test_definition_set_hash_and_semantic_changes():
    from nyx.report_policy import definition_digest
    definition = json.loads(next((ROOT / 'config/report-vocabularies/sha256').glob('*.json')).read_bytes())
    assert definition_digest(definition) == DIGEST
    reordered = json.loads(json.dumps(definition, sort_keys=True, indent=4))
    reordered['entries'].reverse()
    assert definition_digest(reordered) == DIGEST
    for field in ('property', 'artifact_scope', 'value_shape', 'report_meaning', 'label', 'description'):
        changed = copy.deepcopy(definition)
        changed['entries'][0][field] += 'changed'
        changed['entries'].sort(key=lambda e: hashing.canonical_json(e).encode('utf-8'))
        assert hashlib.sha256(hashing.canonical_json(changed).encode('utf-8')).hexdigest() != DIGEST
