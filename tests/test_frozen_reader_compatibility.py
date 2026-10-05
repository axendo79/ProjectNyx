"""Characterizes shipped frozen-reader behavior (valid-time worksheet E12; ADR 0034 section 10). Not a contract for projector 3."""

from contextlib import closing

import pytest

from nyx import events, projection, storage
from test_incremental_commitment import submit_fixture
from test_reducer_boundary import T1, T2, claim, decoded, event, mention

BEFORE = '2026-07-13T00:00:02Z'


def prefix():
    first = event(events.ENTITY_MENTION_RECORDED, mention())
    second = event(events.OBSERVATION_RECORDED, {'claims': [claim()]}, 2, first)
    return [first, second]


def later(log, kind):
    return event(kind, {'claim': claim('c-new', value='32GB'), 'targets': ['c-a'],
                        'basis': {'kind': 'stated_error', 'statement': 'probe'}}, 3, log[-1])


def raw_append(conn, pair):
    # Disposable fixture only, as in mutation_campaign: direct SQL bypasses
    # admission, preserving the complete valid envelope/hash chain and payload.
    envelope, payload = pair
    columns = storage._EVENT_COLUMNS
    with conn:
        conn.execute(f"INSERT INTO events ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                     tuple(getattr(envelope, name) for name in columns))
        conn.execute('INSERT INTO payloads VALUES (?,?,?,?,?)',
                     (payload.event_id, payload.payload_hash, payload.canonical_entity_id,
                      payload.ciphertext, payload.redacted))


def test_unknown_later_event_refuses_snapshot_even_before_cutoff():
    log = prefix()
    with pytest.raises(NotImplementedError, match="^unsupported event_type: 'x_unsupported_probe'$"):
        projection.project_snapshot(decoded([*log, later(log, 'x_unsupported_probe')]), BEFORE, '2')


def test_unknown_later_event_refuses_rebuild_and_preserves_publication(tmp_path):
    log = prefix()
    with closing(storage.init_db(tmp_path / 'probe.db', create=True)) as conn:
        for pair in log:
            submit_fixture(conn, pair, BEFORE, '2')
        before = tuple(conn.iterdump())
        raw_append(conn, later(log, 'x_unsupported_probe'))
        appended = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match="^unsupported event_type: 'x_unsupported_probe'$"):
            storage.rebuild_projection(conn, BEFORE, '2')
        assert tuple(conn.iterdump()) == appended
        assert storage.read_snapshot(conn, '2').complete() == projection.project_snapshot(decoded(log), BEFORE, '2').complete()
        assert appended != before


def test_correction_after_cutoff_is_validated_but_not_reduced():
    log = prefix()
    expected = projection.project_snapshot(decoded(log), BEFORE, '2')
    actual = projection.project_snapshot(decoded([*log, later(log, events.CORRECTION_APPENDED)]), BEFORE, '2')
    assert actual.complete() == expected.complete()
    assert actual.log_position == expected.log_position


def test_correction_reached_by_cutoff_refuses_at_reduction():
    log = prefix()
    with pytest.raises(NotImplementedError, match='correction_appended'):
        projection.project_snapshot(decoded([*log, later(log, events.CORRECTION_APPENDED)]), T2, '2')


def test_shared_recording_time_includes_both_ordinary_observations():
    first = event(events.ENTITY_MENTION_RECORDED, mention(), recorded_at=T1)
    second = event(events.OBSERVATION_RECORDED, {'claims': [claim()]}, 2, first, recorded_at=T1)
    third = event(events.OBSERVATION_RECORDED, {'claims': [claim('c-second')]}, 3, second, recorded_at=T1)
    result = projection.project_snapshot(decoded([first, second, third]), T1, '2')
    assert set(result.beliefs()['b-a']['claim_candidates'][i]['claim_candidate_id'] for i in range(2)) == {'c-a', 'c-second'}
    assert result.log_position == 3
