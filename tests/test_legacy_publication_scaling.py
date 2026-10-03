"""Legacy publication loads only the single prior consumed by the frozen fold."""

from contextlib import closing
from datetime import datetime
import sqlite3

import pytest

from nyx import ingestion, projection, storage, writer
from nyx.reducer import EventDelta

AT = '2026-07-13T12:00:00Z'


def request(index, belief_id=None, correction=False):
    return writer.prepare_event(
        event_type='correction_appended' if correction else 'observation_recorded',
        origin_type='observed', source={'actor_id': 'legacy-scaling', 'config': {}},
        source_class='direct_observation', occurred_at=AT, event_id=f'e-{index}',
        payload={'belief_id': belief_id or f'b-{index}', 'value': f'v-{index}',
                 'verifiability': 'externally_checkable'})


def test_legacy_publication_belief_loads_scale_linearly(tmp_path, monkeypatch):
    original = storage.read_belief
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(storage, 'read_belief', counted)
    counts = []
    for size in (16, 32):
        calls = 0
        with closing(storage.init_db(tmp_path / f'{size}.db', create=True, clock=lambda: AT)) as conn:
            for index in range(size):
                ingestion.submit(conn, request(index), AT, '0')
        counts.append(calls)
    small, large = counts
    print(f'beliefs=16/32, read_belief calls={small}/{large}')
    assert small > 0
    assert 1.8 * small <= large <= 2.2 * small


def full_snapshot_publication(conn, as_of):
    """The pre-optimization publication algorithm, used as a byte/order oracle."""
    applied = 0
    while True:
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            snapshot = storage._read_snapshot(conn, '0')
            pending = storage._pending_events(conn, snapshot.log_position, limit=1)
            if not pending or projection._instant(pending[0][1].recorded_at, 'recorded_at') > projection._instant(as_of, 'as_of'):
                return applied
            position, envelope, payload = pending[0]
            key = payload['belief_id']
            delta = EventDelta(envelope.event_id, {
                key: projection.PROJECTORS['0'](snapshot.belief(key), envelope, payload, as_of)})
            storage._publish_delta(conn, '0', position, delta)
        applied += 1


@pytest.mark.parametrize('batch', [False, True])
def test_legacy_publication_matches_full_snapshot_bytes_and_order(tmp_path, monkeypatch, batch):
    dumps, publications = [], []
    publish = storage._publish_delta
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(AT)

    monkeypatch.setattr(storage, 'datetime', FixedDatetime)
    for reference in (True, False):
        trace = []

        def captured(conn, version, position, delta):
            trace.append((position, delta.event_id, delta.beliefs))
            publish(conn, version, position, delta)

        monkeypatch.setattr(storage, '_publish_delta', captured)
        with closing(storage.init_db(tmp_path / f'{reference}.db', create=True, clock=lambda: AT)) as conn:
            for index in range(8):
                pair = writer.assign(request(index, f'b-{index % 3}', index == 6), AT, storage.last_event_hash(conn))
                storage.safe_append_event(conn, *pair, '0')
                if not batch:
                    if reference:
                        full_snapshot_publication(conn, AT)
                    else:
                        storage.materialize_pending(conn, AT, '0')
            if reference:
                full_snapshot_publication(conn, AT)
            else:
                storage.materialize_pending(conn, AT, '0')
            dumps.append(tuple(conn.iterdump()))
            publications.append(trace)
            assert storage.evaluate_whole_view(conn, AT, '0') == {
                f'b-{i}': storage.read_belief(conn, f'b-{i}') for i in range(3)}
    assert dumps[0] == dumps[1]
    assert publications[0] == publications[1]


@pytest.mark.parametrize('table', ['resolved_beliefs', 'derived_progress'])
def test_legacy_publication_failure_rolls_back_and_retry_matches_replay(tmp_path, table):
    with closing(storage.init_db(tmp_path / 'retry.db', create=True, clock=lambda: AT)) as conn:
        ingestion.submit(conn, request(0), AT, '0')
        storage.append_submission(conn, request(1, 'b-0'), '0')
        with conn:
            conn.execute(f"CREATE TRIGGER fail_publication BEFORE INSERT ON {table} "
                         "BEGIN SELECT RAISE(ABORT, 'publication fault'); END")
        before = tuple(conn.iterdump())
        with pytest.raises(sqlite3.IntegrityError, match='publication fault'):
            storage.materialize_pending(conn, AT, '0')
        assert tuple(conn.iterdump()) == before
        with conn:
            conn.execute('DROP TRIGGER fail_publication')
        assert storage.materialize_pending(conn, AT, '0') == 1
        assert storage.materialize_pending(conn, AT, '0') == 0
        expected = storage.evaluate_whole_view(conn, AT, '0')
        assert expected == {'b-0': storage.read_belief(conn, 'b-0')}


@pytest.mark.parametrize('damage', ['missing', 'wrong_event'])
def test_legacy_publication_preserves_unproven_progress_refusal(tmp_path, damage):
    with closing(storage.init_db(tmp_path / 'progress.db', create=True, clock=lambda: AT)) as conn:
        ingestion.submit(conn, request(0), AT, '0')
        with conn:
            if damage == 'missing':
                conn.execute('DELETE FROM derived_progress')
            else:
                conn.execute("UPDATE derived_progress SET event_id='wrong'")
        before = tuple(conn.iterdump())
        for publish in (full_snapshot_publication, lambda conn, at: storage.materialize_pending(conn, at, '0')):
            with pytest.raises(RuntimeError, match='recover by full replay'):
                publish(conn, AT)
            assert tuple(conn.iterdump()) == before
