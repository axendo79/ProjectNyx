"""Pinned public ADR importer. Retain complete requests before any submission.

Manifests are operational data BESIDE the store, preserved with backup bundles.
They are not a writer queue or a commit acknowledgment. No matching, renames,
authority inference, Git-report claims or recording-time overrides occur here.
"""
from dataclasses import asdict, dataclass, fields as dataclass_fields
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from . import adr_literals, hashing, ingestion, integrity, skeleton, storage, writer
from .ids import new_event_id
from .report_policy import ReportPolicyError, fields, git, strict_json, subject_scope

FORMAT = 'nyx.adr-import-requests/1'


def selected(projector_version):
    if projector_version not in ('1', '2'): raise ValueError('reports require explicit projector_version "1" or "2"')


@dataclass(frozen=True)
class Artifact:
    repository: str
    revision: str
    path: str
    blob: str
    data: bytes

    @property
    def binding(self):
        return self.repository, self.revision, self.path, self.blob

    @property
    def descriptor(self):
        return {'kind': 'adr-path', 'repository': self.repository, 'revision': self.revision,
                'path': self.path, 'blob': self.blob,
                'subject_scope': subject_scope(self.repository, self.path)}


def read_artifacts(policy, repository, revision, paths):
    if not isinstance(paths, (list, tuple)) or not paths or len(paths) != len(set(paths)):
        raise ReportPolicyError('import: paths must be a nonempty distinct ordered sequence')
    artifacts = []
    for path in paths:
        matches = [a for a in policy.artifacts if a[:3] == (repository, revision, path)]
        if len(matches) != 1: raise ReportPolicyError(f'{repository}/{revision}/{path}: outside reviewed public inputs')
        binding = matches[0]
        artifacts.append(Artifact(*binding, git(policy.repositories[repository], 'cat-file', 'blob', binding[3])))
    return artifacts


def imports_dir(conn):
    file = next(row[2] for row in conn.execute('PRAGMA database_list') if row[1] == 'main')
    if not file: raise ReportPolicyError('import requires a file-backed store')
    return Path(file + '.imports')


def manifest_path(conn, run_id):
    if not isinstance(run_id, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', run_id):
        raise ReportPolicyError('import run-id must be one safe path component')
    return imports_dir(conn) / run_id / 'requests.json'


def requests(manifest):
    return [(writer.EventRequest(**r['event_request']), writer.PayloadRequest(**r['payload_request']))
            for r in manifest['requests']]


def read_manifest(path, *, projector_version):
    selected(projector_version)
    manifest = strict_json(Path(path).read_bytes(), path)
    fields(manifest, ('format', 'projector_version', 'associations', 'requests'), path)
    if manifest['format'] != FORMAT or manifest['projector_version'] != projector_version:
        raise ReportPolicyError(f'{path}: retained projector/format mismatch; no retry upgrade')
    if not isinstance(manifest['associations'], list) or not isinstance(manifest['requests'], list):
        raise ReportPolicyError(f'{path}: association set and ordered requests required')
    scopes = set()
    for association in manifest['associations']:
        fields(association, ('scope', 'mention_id', 'subject_id'), path)
        if any(not isinstance(v, str) or not v for v in association.values()):
            raise ReportPolicyError(f'{path}: invalid retained association')
        if association['scope'] in scopes: raise ReportPolicyError(f'{path}: duplicate association scope')
        scopes.add(association['scope'])
    for record in manifest['requests']:
        fields(record, ('event_request', 'payload_request'), path)
        for key, cls in (('event_request', writer.EventRequest), ('payload_request', writer.PayloadRequest)):
            fields(record[key], [f.name for f in dataclass_fields(cls)], path)
    for pair in requests(manifest): writer.validate_request(pair)
    return manifest


def _association(conn, association, projector_version):
    """Validate named recorded associations; never enumerate/match mention text."""
    mention = storage._read_record(conn, 'mentions', association['mention_id'], projector_version)
    link = storage._read_record(conn, 'entity_links', association['mention_id'], projector_version)
    entity = storage._read_record(conn, 'entities', association['subject_id'], projector_version)
    if (mention is None or link is None or entity is None
            or mention['subject_id'] != association['subject_id']
            or mention['text'] != association['scope']
            or link['subject_id'] != association['subject_id']
            or link['link_state'] != 'constitutive' or link['entity_link_confidence'] is not None
            or entity['constituting_mention_id'] != association['mention_id']):
        raise integrity.IntegrityError('missing/inconsistent retained mention/subject association')


def _retained(conn, projector_version):
    retained = {}
    for path in sorted(imports_dir(conn).glob('*/requests.json')):
        raw = strict_json(path.read_bytes(), path)
        # A retained association may have been imported under the other compatible
        # projector. Do not upgrade that manifest; validate its own explicit version.
        manifest = read_manifest(path, projector_version=raw['projector_version'])
        for association in manifest['associations']:
            prior = retained.get(association['scope'])
            if prior is not None and prior != association:
                raise integrity.IntegrityError('ambiguous retained scope associations')
            retained[association['scope']] = association
    for association in retained.values(): _association(conn, association, projector_version)
    # Ensure retention was not lost. This compares recorded IDs and associations,
    # never searches by path/text to discover or reconstruct an identity.
    for envelope, payload in storage.read_all_events(conn):
        config = json.loads(envelope.source).get('config', {})
        if envelope.event_type == 'entity_mention_recorded' and 'report_vocabulary' in config:
            artifact = config.get('report_artifact', {})
            association = {'scope': artifact.get('subject_scope'), 'mention_id': payload['mention_id'],
                           'subject_id': payload['subject_id']}
            if retained.get(association['scope']) != association:
                raise integrity.IntegrityError('missing retained association manifest; cannot remint an import')
    return retained


def _source_dates(data):
    # Original literal Date text is provenance, never a timestamp fallback.
    dates, fence = [], None
    for raw in data.splitlines(keepends=True):
        line = adr_literals._body(raw).decode('utf-8')
        marker = adr_literals.FENCE.match(line)
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1][0], len(marker[1]); continue
        for prefix in ('Date: ', '- **Date:** '):
            if line.startswith(prefix): dates.append(line[len(prefix):])
    return dates


def _persist(path, manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Same-directory replace after data flush; submission starts only on success.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.requests-', suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
        file.write((hashing.canonical_json(manifest) + '\n').encode('utf-8'))
        file.flush()
        os.fsync(file.fileno())
    try: os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def prepare_import(conn, repository, revision, paths, run_id, *, projector_version):
    selected(projector_version)
    policy = conn.report_policy
    if policy is None: raise ReportPolicyError('import requires trusted bound deployment')
    return prepare_artifacts(conn, read_artifacts(policy, repository, revision, paths), run_id,
                             projector_version=projector_version)


def prepare_artifacts(conn, artifacts, run_id, *, projector_version):
    selected(projector_version)
    path = manifest_path(conn, run_id)
    policy = conn.report_policy
    if policy is None: raise ReportPolicyError('import requires trusted bound deployment')
    if not artifacts or len({a.binding for a in artifacts}) != len(artifacts):
        raise ReportPolicyError('import requires nonempty distinct artifacts')
    extracted = []
    for artifact in artifacts:
        if artifact.binding not in policy.artifacts: raise ReportPolicyError('artifact outside reviewed public inputs')
        digest = hashlib.new('sha1' if len(artifact.blob) == 40 else 'sha256',
                             b'blob ' + str(len(artifact.data)).encode('ascii') + b'\0' + artifact.data).hexdigest()
        if digest != artifact.blob: raise ReportPolicyError('artifact bytes do not match pinned native Git blob')
        extracted.append(adr_literals.extract_literals(artifact.data))
    if path.exists():
        manifest = read_manifest(path, projector_version=projector_version)
        observed = {hashing.canonical_json(json.loads(r[0].source)['config']['report_artifact'])
                    for r in requests(manifest)}
        expected = {hashing.canonical_json(a.descriptor) for a in artifacts}
        # A retained path's zero-field revision produces no request. Every
        # field-bearing revision must still be represented, with no extras.
        required = {hashing.canonical_json(a.descriptor)
                    for a, literals in zip(artifacts, extracted) if literals}
        if (not observed.issubset(expected) or not required.issubset(observed)
                or {a['scope'] for a in manifest['associations']} != {a.descriptor['subject_scope'] for a in artifacts}):
            raise ReportPolicyError('run-id already retains different artifact requests')
        return path
    with conn.append_lock:
        storage.materialize_pending(conn, skeleton._live_as_of(conn), projector_version)
        retained = _retained(conn, projector_version)
        associations, prepared, planned_beliefs = [], [], {}
        for artifact, literals in zip(artifacts, extracted):
            scope = artifact.descriptor['subject_scope']
            association = retained.get(scope)
            fresh = association is None
            if fresh:
                association = {'scope': scope, 'mention_id': new_event_id(), 'subject_id': new_event_id()}
                retained[scope] = association
            associations.append(association)
            occurred_at = writer.clock_now()  # One import sample per artifact unit, retained forever.
            source = {'actor_id': 'adr-importer', 'config': {
                'report_vocabulary': policy.declaration, 'report_artifact': artifact.descriptor,
                'report_locations': {}, 'extractor': 'nyx.adr-literal/1',
                'source_dates': _source_dates(artifact.data)}}
            if fresh:
                prepared.append(ingestion.prepare_mention(conn, mention_id=association['mention_id'],
                    subject_id=association['subject_id'], text=scope, source=source,
                    source_class='adr-importer', occurred_at=occurred_at, origin_type='observed'))
            if literals:
                claims, locations = [], {}
                for literal in literals:
                    candidate_id = new_event_id()
                    current = storage.lookup_current_belief_id(conn, association['subject_id'],
                                                               literal['property_id'], projector_version)
                    pair = (association['subject_id'], literal['property_id'])
                    if current is None:
                        current = planned_beliefs.setdefault(pair, new_event_id())
                    claims.append({'mention_id': association['mention_id'], 'subject_id': association['subject_id'],
                        'belief_id': current,
                        'claim_candidate_id': candidate_id, 'property_id': literal['property_id'],
                        'value': literal['value'], 'verifiability': 'externally_checkable'})
                    locations[candidate_id] = literal['location']
                source['config']['report_locations'] = locations
                prepared.append(ingestion.prepare_observation(conn, claims=claims, source=source,
                    source_class='adr-importer', occurred_at=occurred_at, projector_version=projector_version))
        manifest = {'format': FORMAT, 'projector_version': projector_version,
                    'associations': hashing.canonical_set(associations),
                    'requests': [{'event_request': asdict(e), 'payload_request': asdict(p)} for e, p in prepared]}
        _persist(path, manifest)
    return path


def check_completion(conn, manifest, *, projector_version):
    selected(projector_version)
    if not conn.in_transaction:
        with conn:
            conn.execute('BEGIN')
            return check_completion(conn, manifest, projector_version=projector_version)
    status = storage.read_projection_status(conn, projector_version)
    progress = status['derived_progress']
    log_tip = conn.execute('SELECT coalesce(max(rowid),0) FROM events').fetchone()[0]
    position = 0 if progress is None else progress['log_position']
    if status['stale'] or position != log_tip:
        raise integrity.IntegrityError('import completion requires publication at the exact log tip')
    for association in manifest['associations']: _association(conn, association, projector_version)
    candidates = []
    for envelope, payload in requests(manifest):
        stored = storage._recorded_pair(conn, envelope.event_id)
        if stored is None or writer.semantic_contents(*stored) != writer.semantic_contents(envelope, payload):
            raise integrity.IntegrityError('expected complete import request not committed')
        for claim in json.loads(payload.ciphertext).get('claims', []):
            candidate = storage.read_claim_candidate(conn, claim['claim_candidate_id'], projector_version)
            if (candidate is None or any(candidate.get(k) != v for k, v in claim.items())
                    or candidate['supporting_events'] != [envelope.event_id]
                    or candidate['source'] != json.loads(envelope.source)):
                raise integrity.IntegrityError('expected literal claim/scope/support absent from publication')
            candidates.append(claim['claim_candidate_id'])
    return {'projector_version': projector_version, 'publication': {'log_position': position, 'stale': False},
            'claim_candidate_ids': candidates}


def resume_import(conn, run_id, *, projector_version):
    selected(projector_version)
    manifest = read_manifest(manifest_path(conn, run_id), projector_version=projector_version)
    with conn.append_lock:
        for pair in requests(manifest):
            ingestion.submit(conn, pair, skeleton._live_as_of(conn), projector_version)
        # The ordinary writer samples recording time after submit's caller cutoff.
        # Sample at the publication boundary, including a clamped committed tip.
        storage.materialize_pending(conn, skeleton._live_as_of(conn), projector_version)
        return check_completion(conn, manifest, projector_version=projector_version)
