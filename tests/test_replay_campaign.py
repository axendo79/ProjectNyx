"""Bounded fixed-seed whole-publication/replay regression across projectors."""
import importlib.util
from pathlib import Path

import pytest


def load_campaign():
    path = Path(__file__).resolve().parents[1] / 'scripts/replay_campaign.py'
    spec = importlib.util.spec_from_file_location('replay_campaign', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('projector_version', ['0', '1', '2'])
@pytest.mark.parametrize('seed', [0, 17, 902467])
def test_fixed_seed_replay_equivalence(tmp_path, projector_version, seed):
    campaign = load_campaign()
    result = campaign.exercise(tmp_path / 'nyx.db', projector_version, seed, 24, check_prefixes=True)
    assert result['events'] == 24
    assert result['retries'] == 24
    assert result['seed'] == seed


def test_generator_is_deterministic_and_varies_required_dimensions():
    campaign = load_campaign()
    for projector_version in ('0', '1', '2'):
        first = campaign.generate(projector_version, 17, 80)
        assert first == campaign.generate(projector_version, 17, 80)
        assert first != campaign.generate(projector_version, 18, 80)
        values = [step['data'].get('value') for step in first] if projector_version == '0' else [
            claim['value'] for step in first for claim in step['data'].get('claims', [])]
        assert '' in values and 'é' in values and 'e\u0301' in values
        assert any(len(value) >= 4096 for value in values)
        assert len({step['source']['actor_id'] for step in first}) == 4
        assert any(a['recorded_at'] == b['recorded_at'] for a, b in zip(first, first[1:]))
