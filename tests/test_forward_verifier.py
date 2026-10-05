"""Projector 3's independent audits and disposable-store campaigns."""
from contextlib import closing
import pytest
from nyx import committed, committed_storage, forward, projection, storage
from test_forward_correction import append
from test_forward_reads import transition_log
from test_verify_store import verifier
from test_replay_campaign import load_campaign
from test_crash_campaign import harness as crash_harness
from test_mutation_campaign import harness as mutation_harness


def test_independent_clean_audit_and_each_prefix(tmp_path, monkeypatch):
    path = tmp_path / 'store.db'
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in transition_log():
            append(conn, pair)
            report = verifier['verify_store'](path, '3')
            assert report['ok'], report
            assert report['checked']['lineage'] > 0 or report['event_count'] == 1
    def forbidden(*args, **kwargs): raise AssertionError('audit called production reconstruction')
    for module, name in ((storage, 'read_snapshot'), (committed_storage, 'read_snapshot_for'),
                         (forward.Projector, 'reduce'), (projection, 'project_snapshot'),
                         (committed, 'reduce_claims')):
        monkeypatch.setattr(module, name, forbidden)
    report = verifier['verify_store'](path, '3')
    assert report['ok'], report
    assert report['checked']['relations'] >= 3


@pytest.mark.parametrize('case', ['candidate_relations/projector_version/delete',
    'candidate_relations/relation/flip', 'candidate_relations/event_id/flip',
    'candidate_relations/log_position/flip', 'candidates/live_status/rehash',
    'nodes/branch/rehash', 'committed_roots/root_hash/flip'])
def test_relation_and_committed_mutation_campaign(tmp_path, case):
    campaign = mutation_harness()
    path = tmp_path / 'mutant.db'
    campaign.build(path, '3', 17, 12)
    assert case in campaign.cases(path, '3')
    assert campaign.mutate(path, '3', case)
    result = campaign.classify(path, '3', case)
    assert result['outcome'] == 'CAUGHT', result
    assert result['checks']


@pytest.mark.parametrize('seed', [0, 17, 902467])
def test_forward_replay_campaign(tmp_path, seed):
    campaign = load_campaign()
    steps = campaign.generate('3', seed, 24)
    assert steps == campaign.generate('3', seed, 24)
    assert {'correction_appended', 'candidate_replaced', 'candidate_expired'} <= {s['event_type'] for s in steps}
    result = campaign.exercise(tmp_path / 'store.db', '3', seed, 24, check_prefixes=True)
    assert result['retries'] == 24


@pytest.mark.parametrize('point', ['before_append_commit', 'after_append', 'mid_publication',
                                 'mid_rebuild', 'after_publication'])
def test_forward_process_crash_campaign(tmp_path, point):
    result = crash_harness().exercise(tmp_path, '3', 17, point)
    assert result['events_after_retry'] == 7
    assert result['retries'] == 8
