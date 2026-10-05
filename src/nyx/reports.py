"""Named report details: artifact A at revision R stated X, never world truth.

Only recorded provenance and one consistent published prefix are read. There is
no policy lookup, source fetch, publication, listing, coalescing or scalar head.
"""
from dataclasses import asdict
from collections.abc import Sequence
import json
import re

from . import hashing, integrity, storage

PROPERTIES = frozenset(('adr.title.literal', 'adr.status.literal', 'adr.implementation.literal'))
VOCABULARY_FIELDS = frozenset(('identity', 'version', 'digest_algorithm',
                             'canonicalization_profile', 'definition_digest'))
ARTIFACT_FIELDS = frozenset(('kind', 'repository', 'path', 'revision', 'blob', 'subject_scope'))


def _require(condition, reason):
    if not condition: raise integrity.IntegrityError(f'inconsistent report provenance: {reason}')


def _event(conn, event_id, position, projector_version):
    dependency = storage._read_record(conn, 'events', event_id, projector_version)
    _require(dependency is not None, 'missing published supporting event')
    row = conn.execute('SELECT rowid FROM events WHERE event_id=?', (event_id,)).fetchone()
    _require(row is not None and row[0] <= position, 'event outside published prefix')
    pair = storage._recorded_pair(conn, event_id)
    _require(pair is not None, 'missing Layer A event')
    envelope, payload = pair
    data = json.loads(payload.ciphertext)
    _require(dependency == {'event_id': event_id, 'event_hash': envelope.event_hash,
                           'envelope': asdict(envelope), 'payload': data}, 'event dependency differs from Layer A')
    return envelope, data


def _detail(conn, candidate, position, projector_version):
    try:
        ids = {key: candidate[key] for key in ('claim_candidate_id', 'belief_id', 'mention_id', 'subject_id', 'property_id')}
        _require(all(isinstance(v, str) and v for v in ids.values()), 'invalid named IDs')
        _require(ids['property_id'] in PROPERTIES, 'unsupported literal report property')
        supports = candidate['supporting_events']
        _require(isinstance(supports, list) and len(supports) == 1, 'expected one direct supporting observation')
        envelope, payload = _event(conn, supports[0], position, projector_version)
        _require(envelope.event_type == 'observation_recorded' and envelope.origin_type == 'observed', 'unsupported report event')
        claims = [c for c in payload['claims'] if c['claim_candidate_id'] == ids['claim_candidate_id']]
        _require(len(claims) == 1 and all(candidate[k] == v for k, v in claims[0].items()), 'claim differs from observation')
        source = json.loads(envelope.source)
        _require(candidate['source'] == source and candidate['source_class'] == envelope.source_class
                 and candidate['origin_type'] == envelope.origin_type
                 and candidate['occurred_at'] == envelope.occurred_at
                 and candidate['recorded_at'] == envelope.recorded_at, 'source/times differ from supporting event')
        config = source['config']
        declaration = config['report_vocabulary']
        _require(isinstance(declaration, dict) and set(declaration) == VOCABULARY_FIELDS
                 and all(isinstance(v, str) and v for v in declaration.values()), 'absent/malformed recorded declaration')
        _require(declaration['digest_algorithm'] == 'sha256'
                 and declaration['canonicalization_profile'] == 'nyx.canonical-json/1'
                 and re.fullmatch('[0-9a-f]{64}', declaration['definition_digest']), 'unsupported declaration syntax')
        artifact = config['report_artifact']
        _require(isinstance(artifact, dict) and set(artifact) == ARTIFACT_FIELDS
                 and all(isinstance(v, str) and v for v in artifact.values()), 'absent/malformed artifact')
        _require(artifact['kind'] == 'adr-path' and artifact['subject_scope'] ==
                 'repo-path:' + hashing.canonical_json([artifact['repository'], artifact['path']]), 'artifact scope mismatch')
        _require(all(re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', artifact[k]) for k in ('revision', 'blob')), 'non-native revision/blob')
        _require(config['extractor'] == 'nyx.adr-literal/1', 'unsupported literal extractor')
        location = config['report_locations'][ids['claim_candidate_id']]
        _require(isinstance(location, dict) and set(location) == {'start_line', 'end_line', 'start_byte', 'end_byte'}
                 and all(type(v) is int for v in location.values()), 'invalid source location')
        _require(location['start_line'] >= 1 and location['end_line'] >= location['start_line']
                 and location['start_byte'] >= 0 and location['end_byte'] > location['start_byte'], 'invalid span bounds')
        mention = storage._read_record(conn, 'mentions', ids['mention_id'], projector_version)
        link = storage._read_record(conn, 'entity_links', ids['mention_id'], projector_version)
        subject = storage._read_record(conn, 'entities', ids['subject_id'], projector_version)
        _require(mention is not None and link is not None and subject is not None, 'missing mention/link/subject')
        _require(mention['mention_id'] == link['mention_id'] == ids['mention_id']
                 and subject['subject_id'] == ids['subject_id']
                 and mention['subject_id'] == link['subject_id'] == ids['subject_id']
                 and mention['text'] == artifact['subject_scope']
                 and subject['constituting_mention_id'] == ids['mention_id']
                 and mention['event_id'] == link['event_id'] == subject['event_id']
                 and link['link_state'] == 'constitutive' and link['entity_link_confidence'] is None, 'association mismatch')
        bootstrap, bootstrap_payload = _event(conn, mention['event_id'], position, projector_version)
        _require(bootstrap.event_type == 'entity_mention_recorded'
                 and bootstrap_payload == {'mention_id': ids['mention_id'], 'subject_id': ids['subject_id'],
                                            'text': artifact['subject_scope'], 'link_state': 'constitutive'}, 'bootstrap mismatch')
        status = storage.read_belief_status(conn, ids['belief_id'], projector_version)
        belief = status['belief']
        _require(belief is not None and belief['belief_id'] == ids['belief_id']
                 and belief['subject_id'] == ids['subject_id']
                 and belief['property_id'] == ids['property_id'], 'containing belief mismatch')
        members = [c for c in belief['claim_candidates'] if c['claim_candidate_id'] == ids['claim_candidate_id']]
        _require(members == [candidate], 'named candidate differs from containing belief')
        _require(isinstance(candidate['value'], str) and candidate['value'], 'nonliteral value')
        return {**ids, 'artifact': artifact, 'report_scope': {'meaning': 'artifact_at_revision_stated',
                'vocabulary': declaration, 'artifact_scope': artifact['kind']},
                'value': candidate['value'], 'verification_state': candidate['verification_state'],
                'verifiability': candidate['verifiability'], 'projected_as_of': belief['projected_as_of'],
                'provenance': {'observation_event_id': envelope.event_id, 'occurred_at': envelope.occurred_at,
                    'recorded_at': envelope.recorded_at, 'event_hash': envelope.event_hash,
                    'payload_hash': envelope.payload_hash, 'source': source, 'source_class': envelope.source_class,
                    'origin_type': envelope.origin_type, 'location': location}}, status['stale']
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, integrity.IntegrityError): raise
        raise integrity.IntegrityError(f'inconsistent report provenance: {exc}') from exc


def read_report_details(conn, claim_candidate_ids, *, projector_version):
    """Preserve the requested named sequence; no claim of unrequested completeness."""
    if projector_version not in ('1', '2'): raise ValueError('reports require explicit projector_version "1" or "2"')
    if (not isinstance(claim_candidate_ids, Sequence) or isinstance(claim_candidate_ids, (str, bytes)) or not claim_candidate_ids
            or any(not isinstance(v, str) or not v for v in claim_candidate_ids)
            or len(set(claim_candidate_ids)) != len(claim_candidate_ids)):
        raise ValueError('report IDs must be a nonempty ordered sequence of distinct names')
    if not conn.in_transaction:
        with conn:
            conn.execute('BEGIN')
            return read_report_details(conn, claim_candidate_ids, projector_version=projector_version)
    progress = storage.read_projection_status(conn, projector_version)['derived_progress']
    result, stale = [], False
    for identifier in claim_candidate_ids:
        candidate = storage.read_claim_candidate(conn, identifier, projector_version)
        if candidate is None: raise KeyError(identifier)
        _require(isinstance(candidate, dict) and candidate.get('claim_candidate_id') == identifier,
                 'named candidate slot identifies a different record')
        _require(progress is not None, 'candidate without published progress')
        report, behind = _detail(conn, candidate, progress['log_position'], projector_version)
        result.append(report); stale |= behind
    return {'projector_version': projector_version,
            'publication': {'log_position': progress['log_position'], 'stale': stale}, 'reports': result}
