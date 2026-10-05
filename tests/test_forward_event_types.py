"""ADR 0034 sections 2/10: new types validate; frozen reducers still refuse."""

from contextlib import closing

import pytest

from nyx import events, integrity, projection, storage
from test_frozen_reader_compatibility import BEFORE, prefix, raw_append
from test_incremental_commitment import submit_fixture
from test_reducer_boundary import T2, claim, decoded, event


@pytest.mark.parametrize('name,kind', [
    ('CANDIDATE_REPLACED', 'candidate_replaced'),
    ('CANDIDATE_EXPIRED', 'candidate_expired'),
])
def test_new_transition_constants_and_shared_integrity_admission(name, kind):
    assert getattr(events, name) == kind
    log = prefix()
    pair = transition(log, kind)
    integrity.validate_event(*decoded([pair])[0])


def transition(log, kind):
    payload = {'targets': ['c-a'], 'basis': {'kind': 'stated', 'statement': 'probe'}}
    if kind == 'candidate_replaced':
        payload['claim'] = claim('c-next', value='4200')
    else:
        payload['belief_id'] = 'b-a'
    return event(kind, payload, 3, log[-1])


@pytest.mark.parametrize('projector_version', ['1', '2'])
@pytest.mark.parametrize('kind', ['candidate_replaced', 'candidate_expired'])
def test_frozen_snapshot_reads_before_new_type_and_refuses_when_reached(projector_version, kind):
    log = prefix()
    expected = projection.project_snapshot(decoded(log), BEFORE, projector_version)
    extended = decoded([*log, transition(log, kind)])
    actual = projection.project_snapshot(extended, BEFORE, projector_version)
    assert actual.complete() == expected.complete()
    assert actual.log_position == expected.log_position
    with pytest.raises(NotImplementedError, match=f"^stage two refuses '{kind}'$"):
        projection.project_snapshot(extended, T2, projector_version)


@pytest.mark.parametrize('projector_version', ['1', '2'])
@pytest.mark.parametrize('kind', ['candidate_replaced', 'candidate_expired'])
def test_frozen_append_refuses_and_historical_rebuild_works(tmp_path, projector_version, kind):
    log = prefix()
    with closing(storage.init_db(tmp_path / 'probe.db', create=True)) as conn:
        for pair in log:
            submit_fixture(conn, pair, BEFORE, projector_version)
        pair = transition(log, kind)
        before = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match=f"^stage two refuses '{kind}'$"):
            storage.safe_append_event(conn, *pair, projector_version)
        assert tuple(conn.iterdump()) == before
        raw_append(conn, pair)
        expected = projection.project_snapshot(decoded(log), BEFORE, projector_version)
        assert storage.rebuild_projection(conn, BEFORE, projector_version) == expected.beliefs()
        before_reached = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match=f"^stage two refuses '{kind}'$"):
            storage.rebuild_projection(conn, T2, projector_version)
        assert tuple(conn.iterdump()) == before_reached


@pytest.mark.parametrize('kind', ['candidate_replaced', 'candidate_expired'])
def test_legacy_handler_still_refuses_new_types(tmp_path, kind):
    pair = event(kind, {'targets': ['c-a'], 'belief_id': 'b-a',
                        'basis': {'kind': 'stated', 'statement': 'probe'}})
    with closing(storage.init_db(tmp_path / 'legacy.db', create=True)) as conn:
        before = tuple(conn.iterdump())
        with pytest.raises(NotImplementedError, match=f"^append handler for '{kind}' not implemented$"):
            storage.safe_append_event(conn, *pair, '0')
        assert tuple(conn.iterdump()) == before
    with pytest.raises(NotImplementedError, match=f"fold handler for '{kind}' not implemented"):
        projection.project(decoded([pair]), T2, '0')
