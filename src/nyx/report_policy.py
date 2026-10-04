"""ADR 0031 immutable local report admission. Replay never imports this module."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from types import MappingProxyType

from . import hashing


class ReportPolicyError(ValueError):
    """Refusal with a policy file/declaration and reason, before new writes."""


def refuse(context, reason):
    raise ReportPolicyError(f'{context}: {reason}')


def strict_json(data, context):
    def finite(value):
        result = float(value)
        if not math.isfinite(result): refuse(context, 'nonfinite number')
        return result
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: refuse(context, f'duplicate JSON key {key!r}')
            result[key] = value
        return result
    try:
        text = data.decode('utf-8', errors='strict')
        value = json.loads(text, object_pairs_hook=pairs,
                           parse_float=finite,
                           parse_constant=lambda v: refuse(context, f'nonfinite {v}'))
        # Reject escaped lone surrogates, too, before canonical hashing.
        hashing.canonical_json(value).encode('utf-8', errors='strict')
        return value
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ReportPolicyError): raise
        refuse(context, str(exc))


def fields(value, names, context):
    if not isinstance(value, dict) or set(value) != set(names):
        refuse(context, f'expected exactly fields {sorted(names)}')


def text(value, context):
    if not isinstance(value, str) or not value:
        refuse(context, 'expected nonempty exact string')


DECLARATION_FIELDS = ('identity', 'version', 'digest_algorithm',
                      'canonicalization_profile', 'definition_digest')


def declaration(value, context):
    fields(value, DECLARATION_FIELDS, context)
    for key in DECLARATION_FIELDS: text(value[key], f'{context}.{key}')
    if value['digest_algorithm'] != 'sha256': refuse(context, 'unsupported digest algorithm')
    if value['canonicalization_profile'] != 'nyx.canonical-json/1':
        refuse(context, 'unsupported canonicalization profile')
    if not re.fullmatch('[0-9a-f]{64}', value['definition_digest']):
        refuse(context, 'invalid definition digest')
    return tuple(value[key] for key in DECLARATION_FIELDS)


MEANINGS = {
    'adr.title.literal': 'The ADR artifact at the recorded revision stated this literal title.',
    'adr.status.literal': 'The ADR artifact at the recorded revision stated this literal Status declaration.',
    'adr.implementation.literal': 'The ADR artifact at the recorded revision stated this literal Implementation declaration.',
}


def validate_definition(value, context):
    fields(value, ('format', 'identity', 'version', 'label', 'description', 'entries'), context)
    if value['format'] != 'nyx.adr-report-vocabulary/1': refuse(context, 'unsupported format')
    for key in ('identity', 'version'): text(value[key], f'{context}.{key}')
    for key in ('label', 'description'):
        if not isinstance(value[key], str): refuse(context, f'{key} must be a string')
    entries = value['entries']
    if not isinstance(entries, list) or not entries: refuse(context, 'entries must be a nonempty set')
    properties = set()
    for entry in entries:
        fields(entry, ('property', 'value_shape', 'artifact_scope', 'report_meaning', 'label', 'description'), context)
        for key, val in entry.items(): text(val, f'{context}.{key}')
        prop = entry['property']
        if prop in properties: refuse(context, 'duplicate property/entry')
        properties.add(prop)
        if (prop not in MEANINGS or entry['report_meaning'] != MEANINGS[prop]
                or entry['value_shape'] != 'literal-string' or entry['artifact_scope'] != 'adr-path'):
            refuse(context, 'unsupported property/shape/scope/report meaning')
    return {**value, 'entries': sorted(entries, key=lambda e: hashing.canonical_json(e).encode('utf-8'))}


def definition_digest(value):
    validated = validate_definition(value, 'definition')
    return hashlib.sha256(hashing.canonical_json(validated).encode('utf-8')).hexdigest()


def git(checkout, *args, input=None):
    try:
        return subprocess.run(['git', '-C', str(checkout), *args], check=True,
                              capture_output=True, input=input).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        refuse(checkout, f'pinned Git object read failed: {exc}')


def freeze(value):
    if isinstance(value, dict): return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list): return tuple(freeze(v) for v in value)
    return value


@dataclass(frozen=True)
class PolicySnapshot:
    definitions: object
    admitted: frozenset
    artifacts: frozenset
    original_files: object
    repositories: object

    @property
    def declaration(self):
        # This convenience is for the first producer, never an implicit latest.
        matches = [key for key in self.admitted if key[:2] == ('nyx.adr-reports', '1')]
        if len(matches) != 1: refuse('nyx.adr-reports/1', 'not admitted')
        return dict(zip(DECLARATION_FIELDS, matches[0]))


def load_policy(config_dir, *, repositories):
    try:
        return _load_policy(config_dir, repositories=repositories)
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ReportPolicyError): raise
        refuse(config_dir, str(exc))


def _load_policy(config_dir, *, repositories):
    """Resolve every reviewed object before returning a complete frozen bundle."""
    root = Path(config_dir)
    original, definitions, bindings = {}, {}, {}
    def read(path):
        try: data = path.read_bytes()
        except OSError as exc: refuse(path, str(exc))
        original[path.relative_to(root).as_posix()] = data
        return strict_json(data, path)
    files = sorted((root / 'report-vocabularies/sha256').glob('*.json'))
    if not files: refuse(root, 'missing retained vocabulary definitions')
    for path in files:
        value = validate_definition(read(path), path)
        digest = definition_digest(value)
        if path.name != digest + '.json': refuse(path, 'filename/definition digest mismatch')
        binding = (value['identity'], value['version'])
        if binding in bindings and bindings[binding] != digest:
            refuse(path, 'identity/version reassignment')
        bindings[binding] = digest
        key = (*binding, 'sha256', 'nyx.canonical-json/1', digest)
        definitions[key] = value
    path = root / 'report-admission.json'
    allow = read(path)
    fields(allow, ('format', 'admitted'), path)
    if allow['format'] != 'nyx.report-admission/1' or not isinstance(allow['admitted'], list):
        refuse(path, 'invalid admission format/set')
    admitted = set()
    for item in allow['admitted']:
        key = declaration(item, path)
        if key in admitted: refuse(path, 'duplicate admission')
        if key not in definitions: refuse(path, 'unresolved declaration')
        admitted.add(key)
    path = root / 'public-report-inputs.json'
    public = read(path)
    fields(public, ('format', 'artifacts'), path)
    if public['format'] != 'nyx.public-report-inputs/1' or not isinstance(public['artifacts'], list):
        refuse(path, 'invalid public-input format/set')
    entries, artifacts = set(), set()
    for item in public['artifacts']:
        fields(item, ('repository', 'revision', 'path_prefix'), path)
        for key, val in item.items(): text(val, f'{path}.{key}')
        repository, revision, prefix = (item[k] for k in ('repository', 'revision', 'path_prefix'))
        entry = (repository, revision, prefix)
        if entry in entries: refuse(path, 'duplicate public entry')
        entries.add(entry)
        if repository not in repositories: refuse(path, 'repository has no trusted checkout binding')
        if not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', revision): refuse(path, 'revision must be a full commit ID')
        checkout = repositories[repository]
        if git(checkout, 'cat-file', '-t', revision).strip() != b'commit': refuse(path, 'revision is not a commit')
        found = []
        for record in git(checkout, 'ls-tree', '-r', '-z', revision).split(b'\0'):
            if not record: continue
            meta, raw_path = record.split(b'\t', 1)
            name = raw_path.decode('utf-8', errors='strict')
            mode, kind, blob = meta.decode('ascii').split(' ')
            if name.startswith(prefix):
                if kind != 'blob': refuse(path, 'public input is not a blob')
                found.append((repository, revision, name, blob))
        if not found: refuse(path, 'literal prefix expansion matched no blobs')
        checked = git(checkout, 'cat-file', '--batch-check',
                      input=''.join(a[3] + '\n' for a in found).encode('ascii')).splitlines()
        if len(checked) != len(found) or any(len(row.split()) != 3 or row.split()[1] != b'blob' for row in checked):
            refuse(path, 'unavailable pinned blob')
        artifacts.update(found)
    return PolicySnapshot(freeze(definitions), frozenset(admitted), frozenset(artifacts),
                          freeze(original), freeze({k: str(Path(v).resolve()) for k, v in repositories.items()}))
