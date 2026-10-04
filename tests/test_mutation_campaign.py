"""Representative mutations of commitments, publications and freshness."""
import importlib.util
from pathlib import Path

import pytest


def harness():
    path = Path(__file__).resolve().parents[1] / 'scripts/mutation_campaign.py'
    spec = importlib.util.spec_from_file_location('mutation_campaign', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('projector_version', ['0', '1', '2'])
@pytest.mark.parametrize('case', ['events/source_class/flip', 'payloads/ciphertext/delete',
                                'publication/delete', 'derived_progress/event_id/flip',
                                'freshness/delete', 'freshness/swap'])
def test_representative_matrix(tmp_path, projector_version, case):
    campaign = harness()
    path = tmp_path / 'mutation.db'
    campaign.build(path, projector_version, 17, 8)
    campaign.mutate(path, projector_version, case)
    result = campaign.classify(path, projector_version, case)
    assert result['outcome'] == 'CAUGHT', result
    assert result['checks'], result


@pytest.mark.parametrize('case', ['legacy/idempotency_key/rehash', 'legacy/schema_version/rehash',
                                'nodes/content/flip', 'nodes/hash/flip', 'nodes/branch/rehash'])
def test_self_consistent_and_merkle_mutants(tmp_path, case):
    campaign = harness()
    projector_version = '0' if case.startswith('legacy/') else '2'
    path = tmp_path / 'mutation.db'
    campaign.build(path, projector_version, 17, 8)
    campaign.mutate(path, projector_version, case)
    result = campaign.classify(path, projector_version, case)
    assert result['outcome'] == 'CAUGHT', result


@pytest.mark.parametrize('projector_version', ['0', '1', '2'])
def test_clean_campaign_store(tmp_path, projector_version):
    campaign = harness()
    path = tmp_path / 'clean.db'
    campaign.build(path, projector_version, 17, 8)
    assert campaign.verify_store(path, projector_version)['ok']


@pytest.mark.parametrize('projector_version,case', [
    ('0', 'resolved_beliefs/belief_id/duplicate'),
    ('0', 'derived_progress/projector_version/duplicate'),
    ('1', 'projected_entities/projector_version/duplicate'),
    ('1', 'projected_entity_links/link_state/flip'),
    ('1', 'projected_entity_links/entity_link_confidence/flip'),
    ('1', 'belief_event_index/subject_id/swap'),
    ('2', 'committed_nodes/projector_version/duplicate'),
    ('2', 'committed_roots/projector_version/duplicate'),
    ('2', 'projected_beliefs/projector_version/duplicate'),
])
def test_discovered_structural_misses(tmp_path, projector_version, case):
    campaign = harness()
    path = tmp_path / 'mutation.db'
    campaign.build(path, projector_version, 17, 8)
    assert campaign.mutate(path, projector_version, case)
    result = campaign.classify(path, projector_version, case)
    assert result['outcome'] == 'CAUGHT', result


def test_row_permutation_without_content_change_is_a_control(tmp_path):
    campaign = harness()
    path = tmp_path / 'control.db'
    campaign.build(path, '1', 17, 8)
    assert campaign.mutate(path, '1', 'identity_event_index/projector_version/swap') is False
    assert campaign.verify_store(path, '1')['ok']
