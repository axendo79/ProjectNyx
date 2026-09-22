#!/usr/bin/env python3
"""Independently inspect log integrity, projection coverage and commitments.

Only storage.open_readonly is used from the storage API. No normal decoder,
integrity validator, snapshot reader, reducer or projector is called. Hashing
and Merkle construction are shared contract primitives. Reconstruction uses
the shipped legacy and stage-two contracts; it is not a world-truth audit.

Full-log accounting includes pending appends: events beyond validated stored
publication progress are reported as pending, without affecting exit status.
Missing applied events and references absent from the log fail coverage.
Materialized contents are compared at their published
prefix. Evaluation-only projected_as_of is excluded and reported unchecked.
"""

import argparse
from collections import defaultdict
from contextlib import closing
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from nyx import hashing, merkle
from nyx.storage import open_readonly


FIELDS = ('event_id', 'idempotency_key', 'schema_version', 'event_type',
          'occurred_at', 'recorded_at', 'source', 'source_class', 'origin_type',
          'payload_hash', 'entity_refs', 'prev_event_hash', 'event_hash')
KINDS = ('beliefs', 'entities', 'mentions', 'entity_links', 'claim_candidates', 'events')
COLLECTIONS = ('claim_candidates', 'event_dependencies', 'identity_records')
CHECKS = ('envelope_hash', 'chain', 'payload_hash', 'recorded_at', 'coverage', 'merkle', 'lineage')
OBSERVATION = 'observation_recorded'
MENTION = 'entity_mention_recorded'
CORRECTION = 'correction_appended'


def digest(value):
    return hashing._sha256_hex(hashing.canonical_json(value))


def instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError('timestamp has no UTC offset')
    return parsed


class Report:
    def __init__(self, db, version):
        self.data = dict(db=str(db), projector=version,
                        checked=dict.fromkeys(CHECKS, 0), failures=[], unchecked=[], pending=[])

    def check(self, kind, where, condition, message):
        self.data['checked'][kind] += 1
        if not condition:
            self.data['failures'].append(dict(check=kind, location=str(where), message=message))
        return condition

    def skip(self, kind, where, message):
        item = dict(check=kind, location=str(where), message=message)
        if item not in self.data['unchecked']:
            self.data['unchecked'].append(item)

    def result(self):
        return dict(ok=not self.data['failures'], **self.data)


def read_log(conn, report):
    rows = conn.execute('SELECT rowid AS log_position,* FROM events ORDER BY rowid').fetchall()
    payloads = defaultdict(list)
    for row in conn.execute('SELECT * FROM payloads'):
        payloads[row['event_id']].append(dict(row))
    entries, previous_hash, previous_time = [], None, None
    for row in rows:
        envelope = {field: row[field] for field in FIELDS}
        eid = envelope['event_id']
        material = {k: v for k, v in envelope.items() if k not in ('event_hash', 'prev_event_hash')}
        try:
            actual = hashing.event_hash(material, envelope['prev_event_hash'])
            report.check('envelope_hash', eid, actual == envelope['event_hash'], 'envelope hash mismatch')
        except (TypeError, ValueError) as error:
            report.check('envelope_hash', eid, False, f'cannot hash envelope: {error}')
        report.check('chain', eid, envelope['prev_event_hash'] == previous_hash,
                     'predecessor mismatch (genesis requires NULL)' if not entries else 'predecessor does not match previous log row')
        previous_hash = envelope['event_hash']
        try:
            stamp = instant(envelope['recorded_at'])
            if entries and previous_time is None:
                report.skip('recorded_at', eid, 'previous timestamp is invalid; adjacent comparison unavailable')
            else:
                report.check('recorded_at', eid, previous_time is None or stamp >= previous_time,
                             'recorded_at precedes the previous log event')
            previous_time = stamp
        except (TypeError, ValueError) as error:
            report.check('recorded_at', eid, False, f'invalid recorded_at: {error}')
            previous_time = None
        data = None
        matching = payloads.pop(eid, [])
        if report.check('payload_hash', eid, len(matching) == 1, f'expected one payload row; found {len(matching)}'):
            payload = matching[0]
            try:
                if payload['redacted']:
                    report.skip('payload_hash', eid, 'redacted payload: no shipped redacted replay contract')
                else:
                    data = json.loads(payload['ciphertext'])
                    report.check('payload_hash', eid,
                                 digest(data) == envelope['payload_hash'] == payload['payload_hash'],
                                 'payload hash differs from envelope commitment or payload-row hash')
            except (TypeError, ValueError) as error:
                report.check('payload_hash', eid, False, f'missing or invalid payload content: {error}')
        entries.append((row['log_position'], envelope, data))
    for eid in payloads:
        report.check('payload_hash', eid, False, 'orphan payload has no event in the log')
    return entries


class Trees:
    """Traverse raw node rows, then independently rebuild declared roots."""
    def __init__(self, conn, report):
        self.report, self.nodes, self.memo, self.root_cache = report, {}, {}, {}
        report.data['merkle_inventory'] = dict(retained_nodes=0, distinct_roots_rebuilt=0, lineage_headers=0)
        for row in conn.execute("SELECT node_hash,content FROM committed_nodes WHERE projector_version='2'"):
            report.data['merkle_inventory']['retained_nodes'] += 1
            key, raw = row
            try:
                node = json.loads(raw)
                valid = isinstance(node, dict) and node.get('format') == 'nyx-map/1'
                report.check('merkle', key, valid and digest(node) == key and hashing.canonical_json(node) == raw,
                             'stored node hash/encoding differs from canonical content')
                if valid:
                    self.nodes[key] = node
            except (TypeError, ValueError) as error:
                report.check('merkle', key, False, f'invalid node JSON: {error}')
        # Retained historical and unreachable nodes are part of the audit too.
        for key in self.nodes:
            self.members(key, set())

    def members(self, root, active):
        if root == merkle.EMPTY:
            return {}
        if not isinstance(root, str) or not merkle.valid_hash(root):
            self.report.check('merkle', repr(root), False, 'invalid root/child digest')
            return None
        if root in self.memo:
            return self.memo[root]
        if root in active or len(active) > 256:
            self.report.check('merkle', root, False, 'cycle or excessive depth in node graph')
            return None
        node = self.nodes.get(root)
        if node is None:
            self.report.check('merkle', root, False, 'missing referenced node')
            self.memo[root] = None
            return None
        active = active | {root}
        result = None
        if node.get('kind') == 'leaf':
            valid = set(node) == {'format', 'kind', 'key', 'value'} and isinstance(node.get('key'), str) and bool(node['key'])
            if self.report.check('merkle', root, valid, 'invalid leaf fields/key'):
                result = {node['key']: node['value']}
        elif node.get('kind') == 'branch':
            valid = (set(node) == {'format', 'kind', 'bit', 'prefix', 'left', 'right'}
                     and type(node.get('bit')) is int and 0 <= node['bit'] < 256
                     and merkle.valid_hash(node.get('prefix')))
            if self.report.check('merkle', root, valid, 'invalid branch fields'):
                left = self.members(node['left'], active)
                right = self.members(node['right'], active)
                if left is not None and right is not None:
                    valid = bool(left) and bool(right) and not (left.keys() & right.keys())
                    routes = [(merkle.route(k), side) for side, group in enumerate((left, right)) for k in group]
                    valid = valid and all(merkle.prefix(bits, node['bit']) == int(node['prefix'], 16)
                                          and merkle.direction(bits, node['bit']) == side for bits, side in routes)
                    if self.report.check('merkle', root, valid, 'noncanonical branching, duplicate key or wrong child routing'):
                        result = {**left, **right}
        else:
            self.report.check('merkle', root, False, 'invalid stored node kind (empty roots are implicit)')
        self.memo[root] = result
        return result

    def root(self, root, where):
        if isinstance(root, str) and root in self.root_cache:
            return self.root_cache[root]
        members = self.members(root, set())
        if members is not None:
            try:
                rebuilt = merkle.digest(merkle.rebuild(members.items()))
                self.report.data['merkle_inventory']['distinct_roots_rebuilt'] += 1
                self.report.check('merkle', where, rebuilt == root, 'root does not recompute from its leaves')
            except (TypeError, ValueError) as error:
                self.report.check('merkle', where, False, f'cannot reconstruct canonical root: {error}')
                members = None
        if isinstance(root, str):
            self.root_cache[root] = members
        return members


def load_projection(conn, version, report):
    records = {kind: {} for kind in KINDS}
    headers, trees = [], None
    if version == '0':
        for row in conn.execute('SELECT * FROM resolved_beliefs'):
            record = dict(row)
            try:
                for field in ('supporting_events', 'opposing_events', 'superseding_events'):
                    record[field] = json.loads(record[field])
                records['beliefs'][record['belief_id']] = record
            except (TypeError, ValueError) as error:
                report.check('coverage', row['belief_id'], False, f'invalid legacy projection JSON: {error}')
    elif version == '1':
        for kind in KINDS:
            for row in conn.execute(f'SELECT * FROM projected_{kind} WHERE projector_version=?', (version,)):
                try:
                    records[kind][row[1]] = json.loads(row['content'])
                except (TypeError, ValueError) as error:
                    report.check('coverage', row[1], False, f'invalid projected record: {error}')
    elif version == '2':
        trees = Trees(conn, report)
        roots = dict(conn.execute("SELECT kind,root_hash FROM committed_roots WHERE projector_version='2'"))
        if roots:
            report.check('merkle', 'root inventory', set(roots) == {*KINDS, 'current_beliefs'}, 'incomplete or extra index roots')
        for kind, root in roots.items():
            members = trees.root(root, f'index/{kind}')
            if members is not None:
                records[kind] = members
        for key, node in trees.nodes.items():
            value = node.get('value')
            if node.get('kind') == 'leaf' and isinstance(value, dict) and 'collection_roots' in value:
                headers.append((f'node/{key}', value))
        cache = {}
        for bid, raw in conn.execute("SELECT belief_id,content FROM projected_beliefs WHERE projector_version='2'"):
            try:
                cache[bid] = json.loads(raw)
                headers.append((f'header/{bid}', cache[bid]))
            except (TypeError, ValueError) as error:
                report.check('coverage', bid, False, f'invalid cached header JSON: {error}')
        compare_maps('header cache', records['beliefs'], cache, report)
    return records, headers, trees


def clean(record):
    return {k: v for k, v in record.items() if k != 'projected_as_of'} if isinstance(record, dict) else record


def compare_maps(kind, expected, stored, report):
    for key in sorted(expected.keys() | stored.keys()):
        report.check('coverage', f'{kind}/{key}', key in expected and key in stored and
                     hashing.canonical_json(clean(expected.get(key))) == hashing.canonical_json(clean(stored.get(key))),
                     'missing, extra or differing projected record relative to independent reconstruction')


def references(value):
    """Only structural event-reference fields, never arbitrary claim/source data."""
    if isinstance(value, dict):
        for key, member in value.items():
            if key in ('value', 'current_value', 'payload', 'source', 'text'):
                continue
            if key == 'event_id':
                yield member
            elif key in ('event_ids', 'supporting_events', 'opposing_events', 'superseding_events') and isinstance(member, list):
                yield from member
            else:
                yield from references(member)
    elif isinstance(value, list):
        for member in value:
            yield from references(member)


def lineage_record(version, envelope, prior_hash, belief):
    predecessors = [] if prior_hash is None else [{'belief_id': belief['belief_id'], 'view_version_hash': prior_hash}]
    if version == '1':
        return hashing.belief_lineage(version, envelope['event_id'], envelope['event_hash'], predecessors, belief)
    return dict(lineage_format='nyx-belief-lineage/2', projector_version='2',
                producing_event={'event_id': envelope['event_id'], 'event_hash': envelope['event_hash']},
                predecessors=hashing.canonical_set(predecessors),
                result={k: v for k, v in belief.items() if k not in
                        (*COLLECTIONS, 'view_version_hash', 'projected_as_of', 'collection_roots', 'result_root')},
                collection_roots=belief['collection_roots'], result_root=belief['result_root'])


class Replay:
    """Assemble records from recorded claims, not from stored derived inputs.

    Full collection reconstruction is deliberate here. Each belief's previous
    hash comes from this reconstruction, never the header being checked.
    """
    def __init__(self, version, conn):
        self.version, self.conn = version, conn
        self.records = {kind: {} for kind in KINDS}
        self.collections = {}
        self.history = {}

    def append(self, envelope, payload):
        if not isinstance(payload, dict):
            raise ValueError('payload unavailable or not an object')
        eid, event_type = envelope['event_id'], envelope['event_type']
        instant(envelope['occurred_at'])
        if self.version == '0':
            if event_type not in (OBSERVATION, CORRECTION):
                raise NotImplementedError(f'projector 0 has no {event_type} semantics')
            self.legacy(envelope, payload)
            return
        if event_type not in (OBSERVATION, MENTION):
            raise NotImplementedError(f'stage two has no {event_type} semantics')
        records = self.records
        if eid in records['events']:
            raise ValueError('duplicate event identity')
        dependency = dict(event_id=eid, event_hash=envelope['event_hash'], envelope=envelope, payload=payload)
        records['events'][eid] = dependency
        if event_type == MENTION:
            mid, sid = payload['mention_id'], payload['subject_id']
            if payload['link_state'] != 'constitutive' or mid in records['mentions'] or sid in records['entities']:
                raise ValueError('invalid bootstrap or reused identity')
            records['entities'][sid] = dict(subject_id=sid, lifecycle_status='current', constituting_mention_id=mid,
                                           event_id=eid, predecessors=[])
            records['mentions'][mid] = dict(mention_id=mid, subject_id=sid, text=payload['text'], event_id=eid)
            records['entity_links'][mid] = dict(mention_id=mid, subject_id=sid, link_state='constitutive',
                                              entity_link_confidence=None, event_id=eid)
            return
        if envelope['origin_type'] != 'observed':
            raise NotImplementedError('non-observed origin-to-state semantics are unimplemented')
        source = json.loads(envelope['source'])
        touched = set()
        if not isinstance(payload.get('claims'), list) or not payload['claims']:
            raise ValueError('observation has no claim collection')
        for claim in payload['claims']:
            bid, cid, sid, mid = (claim[k] for k in ('belief_id', 'claim_candidate_id', 'subject_id', 'mention_id'))
            if cid in records['claim_candidates'] or records['mentions'][mid]['subject_id'] != sid:
                raise ValueError('candidate reused or mention/subject mismatch')
            entity, mention, link = records['entities'][sid], records['mentions'][mid], records['entity_links'][mid]
            for other_id, other in records['beliefs'].items():
                if (other['subject_id'], other['property_id']) == (sid, claim['property_id']) and other_id != bid:
                    raise ValueError('duplicate subject/property belief')
            if bid in records['beliefs'] and (records['beliefs'][bid]['subject_id'], records['beliefs'][bid]['property_id']) != (sid, claim['property_id']):
                raise ValueError('belief changes subject/property')
            candidate = dict(claim, verification_state='verified',
                verification_basis={'kind': 'direct_observation', 'event_ids': [eid]},
                supporting_events=[eid], opposing_events=[], superseding_events=[], restrictions=[], predecessors=[],
                occurred_at=envelope['occurred_at'], recorded_at=envelope['recorded_at'], source=source,
                source_class=envelope['source_class'], origin_type=envelope['origin_type'],
                provenance_paths=[[{'event_id': link['event_id'], 'mention_id': mid, 'subject_id': sid},
                                   {'event_id': eid, 'belief_id': bid, 'claim_candidate_id': cid}]])
            records['claim_candidates'][cid] = candidate
            groups = self.collections.setdefault(bid, {k: {} for k in COLLECTIONS})
            groups['claim_candidates'][cid] = candidate
            identity = dict(entity=entity, mention=mention, link=link)
            groups['identity_records'][hashing.canonical_json(identity)] = identity
            groups['event_dependencies'][eid] = dependency
            groups['event_dependencies'][link['event_id']] = records['events'][link['event_id']]
            records['beliefs'].setdefault(bid, dict(belief_id=bid, subject_id=sid, property_id=claim['property_id'],
                                                   lifecycle_status='current', predecessors=[], resolution_status='no_authoritative_head'))
            touched.add(bid)
        for bid in sorted(touched):
            belief = records['beliefs'][bid]
            prior = belief.get('view_version_hash')
            belief['updated_at'] = envelope['recorded_at']
            if self.version == '1':
                belief.update({k: hashing.canonical_set(list(v.values())) for k, v in self.collections[bid].items()})
            else:
                roots = {k: merkle.digest(merkle.rebuild(v.items())) for k, v in self.collections[bid].items()}
                belief.update(collection_roots=roots, result_root=digest({'format': 'nyx-result/1', 'collections': roots}))
            record = lineage_record(self.version, envelope, prior, belief)
            belief['view_version_hash'] = digest(record)
            self.history[(bid, eid)] = (prior, deepcopy(belief))

    def legacy(self, envelope, payload):
        bid = payload['belief_id']
        belief = self.records['beliefs'].get(bid)
        older = belief is not None and instant(envelope['occurred_at']) < instant(belief['value_occurred_at'])
        if older and envelope['event_type'] == CORRECTION:
            raise ValueError('backdated correction has no accepted semantics')
        if belief is None:
            belief = dict(belief_id=bid, supporting_events=[], opposing_events=[], superseding_events=[], view_version_hash='')
        belief['supporting_events'].append(envelope['event_id'])
        if envelope['event_type'] == CORRECTION:
            belief['superseding_events'].append(envelope['event_id'])
        if not older:
            if envelope['origin_type'] != 'observed':
                raise NotImplementedError('non-observed origin-to-state semantics are unimplemented')
            value = payload['value']
            # SQLite TEXT affinity is part of the shipped legacy representation.
            if isinstance(value, (int, float)):
                value = self.conn.execute('SELECT CAST(? AS TEXT)', (value,)).fetchone()[0]
            belief.update(current_value=value, value_occurred_at=envelope['occurred_at'], verification_state='verified',
                          verifiability=payload['verifiability'], display_origin=envelope['origin_type'],
                          resolution_basis=('direct observation (world-oracle class, Inv. 4)' if envelope['event_type'] == OBSERVATION
                                            else 'correction supersedes prior value (Inv. 6 superseding event)'))
        belief['view_version_hash'] = hashing._sha256_hex(belief['view_version_hash'] + envelope['event_hash'])
        belief['updated_at'] = envelope['recorded_at']
        self.records['beliefs'][bid] = belief


def check_headers(headers, trees, replay, entries, report):
    log = {envelope['event_id']: (position, envelope) for position, envelope, _ in entries}
    for where, header in headers:
        report.data['merkle_inventory']['lineage_headers'] += 1
        try:
            roots = header['collection_roots']
            if not report.check('merkle', where, isinstance(roots, dict) and set(roots) == set(COLLECTIONS), 'invalid collection-root inventory'):
                continue
            report.check('merkle', where, digest({'format': 'nyx-result/1', 'collections': roots}) == header['result_root'], 'result root does not bind collection roots')
            groups = {k: trees.root(v, f'{where}/{k}') for k, v in roots.items()}
            for kind, members in groups.items():
                if members is not None:
                    for key, member in members.items():
                        if not isinstance(member, dict):
                            report.check('merkle', f'{where}/{kind}/{key}', False, 'collection member is not a record')
                            continue
                        expected_key = (hashing.canonical_json(member) if kind == 'identity_records' else
                                        member.get('claim_candidate_id' if kind == 'claim_candidates' else 'event_id'))
                        report.check('merkle', f'{where}/{kind}/{key}', key == expected_key, 'incorrect collection member key')
                        for ref in references(member):
                            report.check('coverage', where, isinstance(ref, str) and ref in log, f'projected reference absent from log: {ref!r}')
            dependencies = groups['event_dependencies']
            if not dependencies or any(k not in log for k in dependencies):
                report.skip('lineage', where, 'cannot identify producing event from complete dependencies')
                continue
            eid = max(dependencies, key=lambda k: log[k][0])
            expected = replay.history.get((header['belief_id'], eid))
            if expected is None:
                report.skip('lineage', where, 'no independently reconstructible belief history for producing event')
                continue
            prior, expected_header = expected
            record = lineage_record('2', log[eid][1], prior, header)
            report.check('lineage', where, digest(record) == header['view_version_hash'], 'lineage does not commit to result and independently reconstructed predecessor')
            report.check('lineage', where, clean(header) == expected_header, 'header/collections differ from independently reconstructed event result')
        except (KeyError, TypeError, ValueError) as error:
            report.check('lineage', where, False, f'malformed lineage-bearing header: {error}')


def verify_connection(conn, version, report):
    conn.row_factory = sqlite3.Row
    conn.execute('BEGIN')  # One consistent snapshot for log, roots and progress.
    entries = read_log(conn, report)
    report.data['event_count'] = len(entries)
    if version not in ('0', '1', '2'):
        for kind in ('coverage', 'merkle', 'lineage'):
            report.skip(kind, version, 'unsupported projector contract')
        return
    records, headers, trees = load_projection(conn, version, report)
    progress = conn.execute('SELECT log_position,event_id FROM derived_progress WHERE projector_version=?', (version,)).fetchone()
    tip = entries[-1][0] if entries else 0
    position = progress[0] if progress else 0
    if progress:
        prefix_valid = report.check('coverage', 'derived_progress', type(position) is int and
                                    any(p == position and e['event_id'] == progress[1] for p, e, _ in entries),
                                    'progress does not identify a log prefix')
        if not prefix_valid:
            position = 0  # Only a loop bound; no publication position is inferred.
    elif version in ('1', '2') and (any(records.values()) or (trees and trees.nodes)):
        prefix_valid = False
        report.check('coverage', 'derived_progress', False, 'materialization exists without a publication checkpoint')
    elif version == '0' and records['beliefs']:
        prefix_valid = False
        report.skip('coverage', 'derived_progress', 'legacy materialization has no recorded applied position')
    else:
        prefix_valid = True
    report.data['freshness'] = dict(state=('unknown' if not prefix_valid or (not progress and version == '0' and records['beliefs']) else
                                          'unpublished' if position < tip else 'current'),
                                   applied_position=progress[0] if progress else None, append_position=tip,
                                   unpublished_events=sum(p > position for p, _, _ in entries) if prefix_valid else None)
    ids = {e['event_id'] for _, e, _ in entries}
    represented = set(records['events']) if version != '0' else set()
    for kind, members in records.items():
        for key, record in members.items():
            for ref in references(record):
                valid = isinstance(ref, str) and ref in ids
                report.check('coverage', f'{kind}/{key}', valid, f'projected reference absent from log: {ref!r}')
                if version == '0' and valid:
                    represented.add(ref)
    for p, envelope, _ in entries:
        if envelope['event_id'] not in represented:
            if not prefix_valid:
                report.skip('coverage', envelope['event_id'], 'missing projected event; publication position is unknown')
                continue
            if p > position:
                report.data['pending'].append(dict(check='coverage', location=envelope['event_id'],
                    log_position=p, applied_position=position, message='committed but unpublished'))
                continue
        report.check('coverage', envelope['event_id'], envelope['event_id'] in represented,
                     'event missing from projection despite publication progress claiming it was applied')
    replay = Replay(version, conn)
    expected = deepcopy(replay.records)
    complete = True
    for p, envelope, payload in entries:
        if not complete:
            report.skip('coverage', envelope['event_id'], 'independent reconstruction unavailable after earlier unsupported/invalid event')
            continue
        try:
            replay.append(envelope, payload)
            if p == position:
                expected = deepcopy(replay.records)
        except NotImplementedError as error:
            complete = False
            report.skip('coverage', envelope['event_id'], str(error))
        except (KeyError, TypeError, ValueError) as error:
            complete = False
            report.check('coverage', envelope['event_id'], False, f'independent reconstruction failed: {error}')
    if complete and prefix_valid:
        for kind in KINDS:
            compare_maps(kind, expected[kind], records[kind], report)
        if version == '2':
            pairs = {hashing.canonical_json([b['subject_id'], b['property_id']]): bid for bid, b in expected['beliefs'].items()}
            compare_maps('current_beliefs', pairs, records.get('current_beliefs', {}), report)
    else:
        report.skip('coverage', 'projection equality', 'complete reconstruction or valid publication prefix unavailable')
    if version == '2':
        check_headers(headers, trees, replay, entries, report)
        # Publication retains immutable nodes (ADR 0025); checking only the
        # surviving current header would miss deletion of historical lineage.
        retained = {header.get('view_version_hash') for where, header in headers
                    if where.startswith('node/') and isinstance(header, dict)
                    and isinstance(header.get('view_version_hash'), str)}
        event_positions = {e['event_id']: p for p, e, _ in entries}
        for (bid, eid), (_, header) in replay.history.items():
            if prefix_valid and event_positions[eid] <= position:
                report.check('lineage', f'{bid}/{eid}', header['view_version_hash'] in retained,
                             'published historical lineage header is absent from retained nodes')
    else:
        report.skip('merkle', version, 'this projector has no ADR 0025 Merkle representation')
        report.skip('lineage', version, 'no separately retained historical lineage records; final lineage compared with reconstructed belief under coverage')
    report.skip('coverage', 'projected_as_of', 'evaluation-only time is not compared; no shared evaluation time was requested')


def verify_store(db, projector='0'):
    report = Report(db, projector)
    try:
        with closing(open_readonly(db)) as conn:
            verify_connection(conn, projector, report)
    except (sqlite3.Error, OSError, ValueError, KeyError, TypeError) as error:
        report.data['failures'].append(dict(check='store', location=str(db), message=f'{type(error).__name__}: {error}'))
    return report.result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--db', required=True)
    parser.add_argument('--projector', default='0')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    result = verify_store(args.db, args.projector)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        for category in ('failures', 'pending', 'unchecked'):
            for item in result[category]:
                print(f"{category.upper()} [{item['check']}] {item['location']}: {item['message']}")
        print('Checked: ' + ', '.join(f'{k}={v}' for k, v in result['checked'].items()))
        print('Freshness: ' + json.dumps(result.get('freshness', {'state': 'unchecked'})))
        if 'merkle_inventory' in result:
            print('Merkle inventory: ' + json.dumps(result['merkle_inventory']))
        print(f"{len(result['failures'])} failures; {len(result['pending'])} pending events; {len(result['unchecked'])} unchecked findings")
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
