"""ADR 0031 immutable local report admission. Replay never imports this module."""
from dataclasses import dataclass
from collections.abc import Mapping
from contextlib import closing
import hashlib
import json
import math
import os
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
                              capture_output=True, input=input,
                              env={**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'}).stdout
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

    def authorize(self, conn, envelope, data, *, projector_version):
        context = f'event {envelope.event_id} report declaration'
        if projector_version not in ('1', '2'):
            refuse(context, 'report-scoped admission requires explicit projector "1" or "2"')
        source = strict_json(envelope.source.encode('utf-8'), context)
        config = source.get('config') if isinstance(source, dict) else None
        if not isinstance(config, dict): refuse(context, 'missing report config')
        key = declaration(config.get('report_vocabulary'), context)
        if key not in self.admitted: refuse(context, 'vocabulary not admitted by startup snapshot')
        artifact = config.get('report_artifact')
        fields(artifact, ('kind', 'repository', 'revision', 'path', 'blob', 'subject_scope'), context)
        if artifact['kind'] != 'adr-path': refuse(context, 'incompatible artifact scope')
        binding = tuple(artifact[k] for k in ('repository', 'revision', 'path', 'blob'))
        for part in binding: text(part, context)
        if binding not in self.artifacts: refuse(context, 'artifact outside reviewed public inputs')
        if artifact['subject_scope'] != subject_scope(artifact['repository'], artifact['path']):
            refuse(context, 'artifact path scope mismatch')
        if config.get('extractor') != 'nyx.adr-literal/1': refuse(context, 'unsupported extractor')
        locations = config.get('report_locations')
        if not isinstance(locations, dict): refuse(context, 'report_locations must be an object')
        if envelope.origin_type != 'observed': refuse(context, 'unsupported report origin')
        if envelope.event_type == 'entity_mention_recorded':
            if locations or data.get('text') != artifact['subject_scope']:
                refuse(context, 'mention requires recorded path scope and empty locations')
        elif envelope.event_type == 'observation_recorded':
            claims = data.get('claims')
            if not isinstance(claims, list) or not claims: refuse(context, 'report requires literal claims')
            entries = {e['property']: e for e in self.definitions[key]['entries']}
            names = []
            for claim in claims:
                if not isinstance(claim, dict): refuse(context, 'claim must be an object')
                prop = claim.get('property_id')
                if not isinstance(prop, str) or prop not in entries: refuse(context, 'undeclared property')
                text(claim.get('value'), context)
                name = claim.get('claim_candidate_id')
                text(name, context)
                names.append(name)
                from . import storage
                mention = storage._read_record(conn, 'mentions', claim.get('mention_id'), projector_version)
                if (mention is None or mention['text'] != artifact['subject_scope']
                        or mention['subject_id'] != claim.get('subject_id')):
                    refuse(context, 'claim mention/subject does not identify the recorded artifact scope')
                location = locations.get(name)
                fields(location, ('start_line', 'end_line', 'start_byte', 'end_byte'), context)
                if any(type(v) is not int for v in location.values()): refuse(context, 'span must use integers')
                if (location['start_line'] < 1 or location['end_line'] < location['start_line']
                        or location['start_byte'] < 0 or location['end_byte'] <= location['start_byte']):
                    refuse(context, 'invalid literal span')
            if len(names) != len(set(names)) or set(names) != set(locations):
                refuse(context, 'candidate/location mismatch')
        else:
            refuse(context, 'unsupported external report event')


def subject_scope(repository, path):
    text(repository, 'repository'); text(path, 'Git path')
    return 'repo-path:' + hashing.canonical_json([repository, path])


@dataclass(frozen=True, init=False)
class ReportDeployment:
    """Trusted construction; give producers this bound deployment, never an open factory.

    Raw SQL, unbound connections and arbitrary Python privileges remain outside
    the controlled in-process boundary. No actor/source field can configure it.
    """
    store: Path
    policy: PolicySnapshot

    def __init__(self, store, config_dir, *, repositories):
        object.__setattr__(self, 'store', Path(store).resolve())
        object.__setattr__(self, 'policy', load_policy(config_dir, repositories=repositories))
        self._inspect_history()

    def _inspect_history(self, conn=None):
        from . import storage
        if conn is None:
            if not self.store.exists(): return
            with closing(storage.open_readonly(self.store)) as readonly:
                return self._inspect_history(readonly)
        for event_id, raw in conn.execute('SELECT event_id,source FROM events'):
            source = strict_json(raw.encode('utf-8'), f'historical event {event_id}')
            config = source.get('config', {})
            if 'report_vocabulary' in config:
                key = declaration(config['report_vocabulary'], f'historical event {event_id}')
                if key not in self.policy.definitions:
                    refuse(f'historical event {event_id}', 'missing retained definition/binding')

    def open_writer(self, *, create=False, clock=None, threshold=None):
        from . import storage
        conn = storage.init_db(self.store, create=create, clock=clock, threshold=threshold,
                               report_policy=self.policy)
        try:
            # Ownership excludes intervening ordinary appends until close.
            # Inspect this connection before exposing it to any producer.
            self._inspect_history(conn)
            return conn
        except BaseException:
            conn.close()
            raise


def guard(conn, envelope, data, *, projector_version):
    policy = getattr(conn, 'report_policy', None)
    if policy is not None:
        policy.authorize(conn, envelope, data, projector_version=projector_version)


def load_policy(config_dir, *, repositories):
    try:
        return _load_policy(config_dir, repositories=repositories)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, ReportPolicyError): raise
        refuse(config_dir, str(exc))


def _load_policy(config_dir, *, repositories):
    """Resolve every reviewed object before returning a complete frozen bundle."""
    root = Path(config_dir)
    if not isinstance(repositories, Mapping) or not repositories:
        refuse(root, 'trusted repository bindings must be a nonempty mapping')
    for repository, checkout in repositories.items():
        text(repository, 'trusted repository identity')
        if not isinstance(checkout, (str, os.PathLike)) or not Path(checkout).is_dir():
            refuse(root, f'invalid trusted checkout binding for {repository}')
        git(checkout, 'rev-parse', '--git-dir')
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
