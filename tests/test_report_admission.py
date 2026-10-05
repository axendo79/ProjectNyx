"""Prospective report admission, frozen trusted binding, and the R4 matrix."""
from contextlib import closing
from dataclasses import replace
import copy
import json

import pytest

from nyx import ingestion, integrity, projection, skeleton, storage, writer
from test_report_policy import ROOT, REPOSITORY, policy_files

AT = '2026-10-04T12:00:00Z'
AS_OF = '2026-10-05T12:00:00Z'


def deployment(tmp_path, config=None):
    from nyx.report_policy import ReportDeployment
    return ReportDeployment(tmp_path / 'store.db', config or ROOT / 'config',
                            repositories={REPOSITORY: ROOT})


def source(policy):
    a = next(a for a in sorted(policy.artifacts) if a[2] == 'decisions/0031-source-report-claims.md')
    from nyx.report_policy import subject_scope
    return {'actor_id': 'adr-importer', 'config': {
        'operator_note': 'keep me', 'report_vocabulary': policy.declaration,
        'report_artifact': dict(zip(('repository', 'revision', 'path', 'blob'), a),
                                kind='adr-path', subject_scope=subject_scope(a[0], a[2])),
        'report_locations': {}, 'extractor': 'nyx.adr-literal/1', 'source_dates': []}}


def mention(conn, policy, src=None):
    src = source(policy) if src is None else src
    return ingestion.prepare_mention(conn, mention_id='m', subject_id='s',
        text=source(policy)['config']['report_artifact']['subject_scope'], source=src,
        source_class='direct_observation', occurred_at=AT, origin_type='observed', event_id='e-m')


def observation(conn, policy):
    src = source(policy)
    src['config']['report_locations'] = {'c': {'start_line': 1, 'end_line': 1, 'start_byte': 2, 'end_byte': 8}}
    return ingestion.prepare_observation(conn, claims=[{'mention_id': 'm', 'subject_id': 's',
        'belief_id': 'b', 'claim_candidate_id': 'c', 'property_id': 'adr.status.literal',
        'value': 'Stated', 'verifiability': 'externally_checkable'}], source=src,
        source_class='direct_observation', occurred_at=AT, event_id='e-o', projector_version='2')


def tip(conn):
    return conn.execute('SELECT count(*) FROM events').fetchone()[0], storage.last_event_hash(conn)


@pytest.mark.parametrize('route', ['safe-legacy', 'locked-legacy'])
@pytest.mark.parametrize('kind', ['mention', 'observation'])
def test_valid_reports_require_explicit_stage_two_projector(tmp_path, route, kind):
    from nyx.report_policy import ReportPolicyError
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        if kind == 'observation':
            ingestion.submit(conn, mention(conn, d.policy), AS_OF, '2')
            request = observation(conn, d.policy)
        else:
            request = mention(conn, d.policy)
        pair = writer.assign(request, AT, storage.last_event_hash(conn))
        before = tip(conn)
        with pytest.raises(ReportPolicyError, match='requires explicit projector "1" or "2"'):
            if route == 'safe-legacy':
                storage.safe_append_event(conn, *pair)
            else:
                with conn:
                    conn.execute('BEGIN IMMEDIATE')
                    storage._append_legacy_locked(conn, *pair)
        assert tip(conn) == before


@pytest.mark.parametrize('route', ['append', 'submit', 'safe', 'direct-stage', 'locked-stage',
    'locked-legacy', 'safe-legacy', 'skeleton-mention', 'skeleton-observation', 'wrapper'])
def test_every_producer_route_refuses_before_mutation(tmp_path, route):
    from nyx.report_policy import ReportPolicyError
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        src = source(d.policy)
        del src['config']['report_vocabulary']
        src['actor_id'], src['source_class'] = 'disguised', 'direct'
        request = mention(conn, d.policy, src)
        pair = writer.assign(request, AT, None)
        before = tip(conn)
        if route.startswith('skeleton') or route == 'wrapper':
            conn.close()
            with pytest.raises(ReportPolicyError):
                if route == 'skeleton-mention': skeleton.record_mention(d, request, '2')
                else:
                    o = writer.prepare_event(event_type='observation_recorded', origin_type='observed',
                        source=src, source_class='direct', occurred_at=AT, payload={'claims': []})
                    if route == 'wrapper': skeleton._record_stage_two(d, 'observation_recorded', o, '2')
                    else: skeleton.record_observation(d, o, '2')
            with closing(storage.open_readonly(d.store)) as read: assert tip(read) == before
        else:
            with pytest.raises(ReportPolicyError):
                if route == 'append': storage.append_submission(conn, request, '2')
                elif route == 'submit': ingestion.submit(conn, request, AS_OF, '2')
                elif route == 'safe': storage.safe_append_event(conn, *pair, '2')
                elif route == 'safe-legacy': storage.safe_append_event(conn, *pair)
                elif route == 'direct-stage': storage._append_stage_two(conn, *pair, '2')
                else:
                    with conn:
                        conn.execute('BEGIN IMMEDIATE')
                        if route == 'locked-stage': storage._append_stage_two_locked(conn, *pair, '2')
                        else: storage._append_legacy_locked(conn, *pair)
            assert tip(conn) == before


@pytest.mark.parametrize('change', ['missing', 'null', 'nonobject', 'missing-field', 'extra',
    'wrong-type', 'empty-identity', 'empty-version', 'algorithm', 'profile', 'digest',
    'mismatch', 'case', 'nfc', 'nfd', 'scope', 'artifact', 'property', 'shape', 'empty-value'])
def test_admission_refusal_matrix(tmp_path, change):
    from nyx.report_policy import ReportPolicyError
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        ingestion.submit(conn, mention(conn, d.policy), AS_OF, '2')
        request = observation(conn, d.policy)
        src, payload = json.loads(request[0].source), json.loads(request[1].ciphertext)
        c, v = src['config'], src['config']['report_vocabulary']
        if change == 'missing': del c['report_vocabulary']
        elif change == 'null': c['report_vocabulary'] = None
        elif change == 'nonobject': c['report_vocabulary'] = []
        elif change == 'missing-field': del v['version']
        elif change == 'extra': v['extra'] = True
        elif change == 'wrong-type': v['version'] = 1
        elif change.startswith('empty-'): 
            if change == 'empty-value': payload['claims'][0]['value'] = ''
            else: v[change[6:]] = ''
        elif change == 'algorithm': v['digest_algorithm'] = 'sha1'
        elif change == 'profile': v['canonicalization_profile'] = 'unknown'
        elif change == 'digest': v['definition_digest'] = 'ABCD'
        elif change == 'mismatch': v['definition_digest'] = '0' * 64
        elif change == 'case': v['identity'] = 'NYX.adr-reports'
        elif change == 'nfc': v['identity'] = '\u00e9'
        elif change == 'nfd': v['identity'] = 'e\u0301'
        elif change == 'scope': c['report_artifact']['kind'] = 'world'
        elif change == 'artifact': c['report_artifact']['blob'] = '0' * 40
        elif change == 'property': payload['claims'][0]['property_id'] = 'adr.status.world'
        elif change == 'shape': payload['claims'][0]['value'] = {'truth': True}
        request = replace(request[0], source=json.dumps(src)), replace(request[1], ciphertext=json.dumps(payload))
        before = tip(conn)
        with pytest.raises(ReportPolicyError): storage.append_submission(conn, request, '2')
        assert tip(conn) == before


def retire(config):
    (config / 'report-admission.json').write_text('{"format":"nyx.report-admission/1","admitted":[]}', encoding='utf-8')


@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_r4_retry_matrix_and_frozen_lifetime(tmp_path, projector_version):
    from nyx.report_policy import ReportPolicyError
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        m, o = mention(conn, d.policy), observation(conn, d.policy)
        original = ingestion.submit(conn, m, AS_OF, projector_version)
        retire(config)
        # Loaded admission and complete original bytes do not change.
        assert ingestion.submit(conn, m, AS_OF, projector_version) == original
        assert d.policy.admitted
        with pytest.raises(AttributeError): conn.report_policy = None
    restarted = deployment(tmp_path, config)
    with closing(restarted.open_writer()) as conn:
        before = tip(conn)
        assert ingestion.submit(conn, m, AS_OF, projector_version) == original
        conflict = replace(m[0], source=m[0].source.replace('keep me', 'changed')), m[1]
        with pytest.raises(integrity.IntegrityError): ingestion.submit(conn, conflict, AS_OF, projector_version)
        with pytest.raises(ReportPolicyError): ingestion.submit(conn, o, AS_OF, projector_version)
        assert tip(conn) == before
        assert storage.read_snapshot(conn, projector_version).beliefs() == {}
    # A still-running owner continues accepting its snapshot even after file edits.
    other = tmp_path / 'other'; other.mkdir()
    live = deployment(other)
    with closing(live.open_writer(create=True)) as conn:
        committed_m = ingestion.submit(conn, mention(conn, live.policy), AS_OF, projector_version)
        committed_o = ingestion.submit(conn, observation(conn, live.policy), AS_OF, projector_version)
    # Retirement also permits equivalent observation retry, not just mention.
    from nyx.report_policy import ReportDeployment
    retired = ReportDeployment(live.store, config, repositories={REPOSITORY: ROOT})
    with closing(retired.open_writer()) as conn:
        assert ingestion.submit(conn, observation(conn, live.policy), AS_OF, projector_version) == committed_o
        assert storage.safe_append_event(conn, *committed_o, projector_version) is False


def test_startup_before_store_and_historical_bundle_inspection(tmp_path):
    from nyx.report_policy import ReportPolicyError
    config = policy_files(tmp_path)
    (config / 'public-report-inputs.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ReportPolicyError): deployment(tmp_path, config)
    assert not (tmp_path / 'store.db').exists()
    assert not (tmp_path / 'store.db.lock').exists()
    config = ROOT / 'config'
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        ingestion.submit(conn, mention(conn, d.policy), AS_OF, '2')
    broken = policy_files(tmp_path / 'broken')
    definition = next((broken / 'report-vocabularies/sha256').glob('*.json'))
    value = json.loads(definition.read_bytes()); value['version'] = '2'
    from nyx.report_policy import definition_digest
    definition.unlink()
    definition.with_name(definition_digest(value) + '.json').write_text(json.dumps(value), encoding='utf-8')
    retire(broken)
    before = d.store.read_bytes()
    with pytest.raises(ReportPolicyError): deployment(tmp_path, broken)
    assert d.store.read_bytes() == before


def test_replay_publication_and_privileged_bypass_are_separate(tmp_path, monkeypatch):
    from nyx.report_policy import PolicySnapshot, ReportPolicyError
    d = deployment(tmp_path)
    with closing(d.open_writer(create=True)) as conn:
        m = mention(conn, d.policy)
        pair = storage.append_submission(conn, m, '2')
        monkeypatch.setattr(PolicySnapshot, 'authorize', lambda *a: (_ for _ in ()).throw(AssertionError('policy consulted')))
        storage.materialize_pending(conn, AS_OF, '2')
        log = storage.read_all_events(conn)
        assert projection.project_snapshot(log, AS_OF, '2').records('mentions')
    # Equivalent privileges are explicitly outside the controlled producer boundary.
    unbound = tmp_path / 'bypass.db'
    with closing(storage.init_db(unbound, create=True, clock=lambda: AT)) as conn:
        undeclared = ingestion.prepare_mention(conn, mention_id='x', subject_id='y', text='external',
            source={'actor_id': 'other'}, source_class='direct', occurred_at=AT, origin_type='observed')
        assigned = writer.assign(undeclared, AT, None)
        columns = storage._EVENT_COLUMNS
        conn.execute(f"INSERT INTO events ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                     tuple(getattr(assigned[0], c) for c in columns))
        p = assigned[1]
        conn.execute('INSERT INTO payloads VALUES (?,?,?,?,?)', (p.event_id, p.payload_hash, None, p.ciphertext, 0))
        conn.commit()
        for projector_version in ('1', '2'):
            conn.execute('INSERT INTO identity_event_index VALUES (?,?,?)', (projector_version, 'y', p.event_id))
        conn.commit()
        storage.materialize_pending(conn, AS_OF, '2')
        assert projection.project_snapshot(storage.read_all_events(conn), AS_OF, '2').records('mentions')
        import sys
        sys.path.insert(0, str(ROOT / 'scripts'))
        from verify_store import verify_store
        result = verify_store(unbound, projector='2')
        assert result['ok'], result


def test_running_owner_ignores_retirement_and_bundle_is_deeply_frozen(tmp_path):
    config = policy_files(tmp_path)
    d = deployment(tmp_path, config)
    with closing(d.open_writer(create=True)) as conn:
        retire(config)
        ingestion.submit(conn, mention(conn, d.policy), AS_OF, '2')
        ingestion.submit(conn, observation(conn, d.policy), AS_OF, '2')
        assert tip(conn)[0] == 2
        with pytest.raises(TypeError): d.policy.definitions[next(iter(d.policy.definitions))]['version'] = '2'


@pytest.mark.parametrize('projector_version', ['1', '2'])
def test_history_added_before_acquisition_refuses_and_releases_owner(tmp_path, monkeypatch, projector_version):
    import sqlite3
    from nyx.report_policy import ReportDeployment, ReportPolicyError, definition_digest
    older = deployment(tmp_path)
    with closing(older.open_writer(create=True)):
        pass
    config = policy_files(tmp_path / 'newer')
    definition_file = next((config / 'report-vocabularies/sha256').glob('*.json'))
    definition = json.loads(definition_file.read_bytes())
    definition['version'] = '2'
    digest = definition_digest(definition)
    definition_file.with_name(digest + '.json').write_text(json.dumps(definition), encoding='utf-8')
    newer_declaration = {**older.policy.declaration, 'version': '2', 'definition_digest': digest}
    admission_file = config / 'report-admission.json'
    admission = json.loads(admission_file.read_bytes())
    admission['admitted'].append(newer_declaration)
    admission_file.write_text(json.dumps(admission), encoding='utf-8')
    newer = ReportDeployment(older.store, config, repositories={REPOSITORY: ROOT})
    acquire, close = writer.acquire, writer.WriterConnection.close
    committed, closed = [], []

    def acquire_after_commit(path):
        if not committed:
            committed.append(None)  # Nested acquisition uses the real seam.
            with closing(newer.open_writer()) as conn:
                src = source(newer.policy)
                src['config']['report_vocabulary'] = newer_declaration
                committed[0] = ingestion.submit(conn, mention(conn, newer.policy, src), AS_OF, projector_version)
        return acquire(path)

    def record_close(conn):
        if conn.report_policy is older.policy and conn.owner_lock is not None:
            closed.append(conn)
        close(conn)

    monkeypatch.setattr(writer, 'acquire', acquire_after_commit)
    monkeypatch.setattr(writer.WriterConnection, 'close', record_close)
    with pytest.raises(ReportPolicyError, match='missing retained definition/binding'):
        with closing(older.open_writer()):
            pass
    assert len(closed) == 1 and closed[0].owner_lock is None
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        closed[0].execute('SELECT 1')
    # A complete bundle can immediately reacquire ownership; refusal did not
    # lose the intervening committed event or leak the writer lock.
    with closing(newer.open_writer()) as conn:
        assert tip(conn) == (1, committed[0][0].event_hash)
