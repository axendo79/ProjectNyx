"""Independent checks must catch corruption without calling normal validators."""

from contextlib import closing
import json
from pathlib import Path
import runpy
import sqlite3

import pytest

from nyx import committed, committed_storage, events, hashing, integrity, merkle, projection, reducer, storage
from test_event_integrity import entries, rehash
from test_reducer_boundary import T0, T2, claim, event, mention


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify_store.py'
verifier = runpy.run_path(str(SCRIPT))


@pytest.fixture(params=['0', '1', '2'])
def database(tmp_path, request):
    version = request.param
    path = tmp_path / 'verify.sqlite'
    with closing(storage.init_db(path, create=True)) as conn:
        log = entries(version)
        for pair in log:
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        yield path, conn, version, log


def verify(database):
    path, _, version, _ = database
    return verifier['verify_store'](path, version)


def targeted(report, check):
    assert not report['ok']
    assert any(f['check'] == check for f in report['failures']), report


def test_clean_store_counts_and_no_mutation(database):
    _, conn, version, log = database
    before = tuple(conn.iterdump())
    report = verify(database)
    assert report['ok'], report['failures']
    assert tuple(conn.iterdump()) == before
    assert report['event_count'] == len(log)
    for check in ('envelope_hash', 'chain', 'recorded_at'):
        assert report['checked'][check] == len(log)
    assert report['checked']['coverage'] >= len(log)
    if version == '2':
        assert report['checked']['merkle'] > 0
        assert report['checked']['lineage'] >= 4  # both event-produced headers and cached head
    else:
        assert any(u['check'] == 'merkle' for u in report['unchecked'])


@pytest.mark.parametrize('damage,check', [
    ('envelope', 'envelope_hash'), ('chain', 'chain'), ('payload', 'payload_hash'),
    ('timestamp', 'recorded_at'), ('coverage', 'coverage'),
])
def test_each_corruption_is_caught_by_its_own_check(database, damage, check):
    _, conn, version, log = database
    env, payload = log[1]
    with conn:
        if damage in ('envelope', 'chain', 'timestamp'):
            conn.execute('DROP TRIGGER no_update_events')
        if damage == 'envelope':
            conn.execute("UPDATE events SET source_class='tampered' WHERE event_id=?", (env.event_id,))
        elif damage == 'chain':
            changed = rehash(env, prev_event_hash='f' * 64)
            conn.execute('UPDATE events SET prev_event_hash=?,event_hash=? WHERE event_id=?',
                         (changed.prev_event_hash, changed.event_hash, env.event_id))
        elif damage == 'payload':
            data = json.loads(payload.ciphertext)
            if version == '0':
                data['value'] = 'tampered'
            else:
                data['claims'][0]['value'] = 'tampered'
            conn.execute('UPDATE payloads SET ciphertext=? WHERE event_id=?', (json.dumps(data), env.event_id))
        elif damage == 'timestamp':
            conn.execute('UPDATE events SET recorded_at=? WHERE event_id=?', (T0, env.event_id))
        elif version == '0':
            conn.execute("UPDATE resolved_beliefs SET supporting_events='[]'")
        elif version == '1':
            conn.execute("DELETE FROM projected_events WHERE event_id=?", (env.event_id,))
        else:
            conn.execute("UPDATE committed_roots SET root_hash=? WHERE kind='events'", (merkle.EMPTY,))
    targeted(verify(database), check)


def test_merkle_root_and_predecessor_lineage_corruption(database):
    _, conn, version, _ = database
    if version != '2':
        pytest.skip('ADR 0025 representation only')
    with conn:
        conn.execute("UPDATE committed_roots SET root_hash=? WHERE kind='beliefs'", ('0' * 64,))
        header = json.loads(conn.execute("SELECT content FROM projected_beliefs WHERE projector_version='2'").fetchone()[0])
        header['view_version_hash'] = 'a' * 64
        conn.execute("UPDATE projected_beliefs SET content=? WHERE projector_version='2'", (hashing.canonical_json(header),))
    report = verify(database)
    targeted(report, 'merkle')
    targeted(report, 'lineage')


def test_rehashed_leaf_cannot_hide_incorrect_root(database):
    _, conn, version, _ = database
    if version != '2':
        pytest.skip('ADR 0025 representation only')
    # Change a leaf beneath an unchanged root, leaving a valid extra node as
    # camouflage; traversal must recompute the actual referenced content.
    key, raw = next((h, raw) for h, raw in conn.execute('SELECT node_hash,content FROM committed_nodes')
                    if json.loads(raw).get('kind') == 'leaf')
    body = json.loads(raw)
    body['value'] = 'altered'
    with conn:
        conn.execute('UPDATE committed_nodes SET content=? WHERE node_hash=?', (hashing.canonical_json(body), key))
    targeted(verify(database), 'merkle')


def test_consistent_merkle_tree_with_wrong_lineage_predecessor_fails(database):
    _, conn, version, log = database
    if version != '2':
        pytest.skip('ADR 0025 lineage only')
    header = json.loads(conn.execute("SELECT content FROM projected_beliefs WHERE projector_version='2'").fetchone()[0])
    env = log[-1][0]
    forged = dict(lineage_format='nyx-belief-lineage/2', projector_version='2',
                  producing_event={'event_id': env.event_id, 'event_hash': env.event_hash},
                  predecessors=[],  # Invalid: this existing belief has a prior lineage.
                  result={k: v for k, v in header.items() if k not in
                          ('view_version_hash', 'projected_as_of', 'collection_roots', 'result_root')},
                  collection_roots=header['collection_roots'], result_root=header['result_root'])
    header['view_version_hash'] = hashing._sha256_hex(hashing.canonical_json(forged))
    written = {}
    root = merkle.put(None, header['belief_id'], header, written)
    with conn:
        for key, raw in written.items():
            conn.execute("INSERT INTO committed_nodes VALUES ('2',?,?)", (key, raw))
        conn.execute("UPDATE committed_roots SET root_hash=? WHERE kind='beliefs'", (merkle.digest(root),))
        conn.execute("UPDATE projected_beliefs SET content=? WHERE projector_version='2'", (hashing.canonical_json(header),))
    report = verify(database)
    assert not [f for f in report['failures'] if f['check'] == 'merkle']
    targeted(report, 'lineage')


@pytest.mark.parametrize('damage', ['missing', 'invalid_json', 'row_hash'])
def test_payload_rows_never_disappear_from_checking(database, damage):
    _, conn, _, log = database
    eid = log[1][0].event_id
    with conn:
        if damage == 'missing':
            conn.execute('DELETE FROM payloads WHERE event_id=?', (eid,))
        elif damage == 'invalid_json':
            conn.execute("UPDATE payloads SET ciphertext='{' WHERE event_id=?", (eid,))
        else:
            conn.execute("UPDATE payloads SET payload_hash='wrong' WHERE event_id=?", (eid,))
    targeted(verify(database), 'payload_hash')


def test_genesis_and_all_failures_are_reported(database):
    _, conn, _, log = database
    with conn:
        conn.execute('DROP TRIGGER no_update_events')
        conn.execute("UPDATE events SET source_class='changed'")
        conn.execute("UPDATE events SET prev_event_hash='bad' WHERE event_id=?", (log[0][0].event_id,))
        conn.execute("UPDATE payloads SET ciphertext='{' WHERE event_id=?", (log[1][0].event_id,))
    report = verify(database)
    assert len([f for f in report['failures'] if f['check'] == 'envelope_hash']) == len(log)
    targeted(report, 'chain')
    targeted(report, 'payload_hash')


def test_normal_read_and_projector_bugs_cannot_make_verifier_pass(database, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('normal read/replay validation called')

    for module, functions in [
        (integrity, ('verified_log', 'validate_event', 'validate_envelope', 'decode_payload')),
        (projection, ('fold', 'project', 'project_snapshot', '_state_for_origin', '_instant')),
        (reducer, ('reduce',)), (committed, ('reduce', 'lineage', 'full_result_roots')),
        (committed_storage, ('read_snapshot',)),
        (storage, ('read_all_events', 'read_snapshot', 'read_belief', 'read_projection_status')),
    ]:
        for name in functions:
            monkeypatch.setattr(module, name, forbidden)
    assert verify(database)['ok']
    with database[1]:
        database[1].execute("UPDATE payloads SET ciphertext='{}'")
    targeted(verify(database), 'payload_hash')


def test_projected_references_to_absent_events_are_caught(database):
    _, conn, version, _ = database
    with conn:
        if version == '0':
            conn.execute('UPDATE resolved_beliefs SET opposing_events=?', ('["absent-event"]',))
        elif version == '1':
            record = json.loads(conn.execute("SELECT content FROM projected_mentions WHERE projector_version='1'").fetchone()[0])
            record['event_id'] = 'absent-event'
            conn.execute("UPDATE projected_mentions SET content=? WHERE projector_version='1'", (json.dumps(record),))
        else:
            root = conn.execute("SELECT root_hash FROM committed_roots WHERE kind='mentions'").fetchone()[0]
            raw = conn.execute('SELECT content FROM committed_nodes WHERE node_hash=?', (root,)).fetchone()[0]
            node = json.loads(raw)
            node['value']['event_id'] = 'absent-event'
            conn.execute('UPDATE committed_nodes SET content=? WHERE node_hash=?', (hashing.canonical_json(node), root))
    report = verify(database)
    assert any(f['check'] == 'coverage' and 'absent from log' in f['message'] for f in report['failures'])


def test_invalid_publication_progress_does_not_claim_freshness(database):
    with database[1]:
        database[1].execute("UPDATE derived_progress SET event_id='absent'")
    report = verify(database)
    targeted(report, 'coverage')
    assert report['freshness']['state'] == 'unknown'


def test_legacy_without_checkpoint_has_unknown_freshness(database):
    if database[2] != '0':
        pytest.skip('legacy checkpoint disclosure')
    with database[1]:
        database[1].execute('DELETE FROM derived_progress')
    report = verify(database)
    assert report['ok'], report['failures']
    assert report['freshness']['state'] == 'unknown'


def test_readonly_opener_blocks_every_write(database, monkeypatch):
    function = verifier['verify_store']
    real_open = function.__globals__['open_readonly']

    def checked_open(path):
        conn = real_open(path)
        for sql in ('CREATE TABLE forbidden(x)', 'DELETE FROM events', 'PRAGMA query_only=OFF',
                    "ATTACH ':memory:' AS other", 'CREATE TEMP TABLE forbidden(x)'):
            with pytest.raises(sqlite3.DatabaseError):
                conn.execute(sql)
        return conn

    monkeypatch.setitem(function.__globals__, 'open_readonly', checked_open)
    assert verify(database)['ok']


@pytest.mark.parametrize('version', ['0', '1', '2'])
def test_unpublished_event_is_pending_without_affecting_exit_status(tmp_path, version, capsys):
    path = tmp_path / 'pending.sqlite'
    log = entries(version)
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log[:2]:
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        storage.safe_append_event(conn, *log[2], version)
    report = verifier['verify_store'](path, version)
    assert report['freshness']['unpublished_events'] == 1
    assert report['freshness']['state'] == 'unpublished'
    assert report['ok'], report['failures']
    assert report['failures'] == []
    assert report['pending'] == [dict(check='coverage', location=log[2][0].event_id,
                                     log_position=3, applied_position=2,
                                     message='committed but unpublished')]
    assert verifier['main'](['--db', str(path), '--projector', version, '--json']) == 0
    assert json.loads(capsys.readouterr().out)['pending'] == report['pending']
    assert verifier['main'](['--db', str(path), '--projector', version]) == 0
    assert 'PENDING [coverage]' in capsys.readouterr().out


@pytest.mark.parametrize('version', ['0', '1', '2'])
def test_progress_claims_event_applied_but_projection_lacks_it(tmp_path, version):
    path = tmp_path / 'false-progress.sqlite'
    log = entries(version)
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log[:2]:
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        storage.safe_append_event(conn, *log[2], version)
        with conn:
            conn.execute('UPDATE derived_progress SET log_position=3,event_id=? WHERE projector_version=?',
                         (log[2][0].event_id, version))
    report = verifier['verify_store'](path, version)
    targeted(report, 'coverage')
    assert report['pending'] == []
    assert any(f['location'] == log[2][0].event_id and 'claiming it was applied' in f['message']
               for f in report['failures'])


@pytest.mark.parametrize('version', ['1', '2'])
def test_multiple_claims_mentions_equal_times_and_arbitrary_values(tmp_path, version):
    path = tmp_path / 'complex.sqlite'
    a = event(events.ENTITY_MENTION_RECORDED, mention())
    b = event(events.ENTITY_MENTION_RECORDED, mention('s-b', 'm-b'), 2, a)
    c = event(events.OBSERVATION_RECORDED, {'claims': [claim(), claim('c-b', 'b-b', 's-b', 'm-b')]}, 3, b)
    d = event(events.OBSERVATION_RECORDED, {'claims': [claim('c-c', value={'event_id': 'literal, not a reference'}), claim('c-d')]},
              4, c, occurred_at=T0, recorded_at=c[0].recorded_at)
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in (a, b, c, d):
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
    report = verifier['verify_store'](path, version)
    assert report['ok'], report['failures']


def test_unknown_version_and_empty_store_are_explicit(tmp_path):
    path = tmp_path / 'empty.sqlite'
    storage.init_db(path, create=True).close()
    for version in ('0', '1', '2', '999'):
        report = verifier['verify_store'](path, version)
        assert report['ok'], report
        assert not report['event_count']
        if version == '999':
            assert {u['check'] for u in report['unchecked']} == {'coverage', 'merkle', 'lineage'}
    absent = tmp_path / 'absent.sqlite'
    assert not verifier['verify_store'](absent)['ok']
    assert not absent.exists()


def test_cli_json_human_and_failing_exit(database, capsys):
    path, conn, version, _ = database
    main = verifier['main']
    assert main(['--db', str(path), '--projector', version, '--json']) == 0
    assert json.loads(capsys.readouterr().out)['ok']
    with conn:
        conn.execute("UPDATE payloads SET ciphertext='{}'")
    assert main(['--db', str(path), '--projector', version]) == 1
    assert 'payload_hash' in capsys.readouterr().out
