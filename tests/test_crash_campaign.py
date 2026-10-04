"""Real process death at append, publication and full-replay boundaries."""
import importlib.util
from pathlib import Path

import pytest


def harness():
    path = Path(__file__).resolve().parents[1] / 'scripts/crash_campaign.py'
    spec = importlib.util.spec_from_file_location('crash_campaign', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('version', ['0', '1', '2'])
@pytest.mark.parametrize('point', ['before_append_commit', 'after_append', 'mid_publication',
                                 'mid_rebuild', 'after_publication'])
def test_killed_writer_recovers_without_loss_or_duplicate(tmp_path, version, point):
    if version == '0' and point == 'mid_rebuild':
        pytest.skip('rebuild_projection supports snapshot projectors 1/2; legacy recovery uses materialize_pending')
    result = harness().exercise(tmp_path, version, 17, point)
    assert result['events_after_retry'] == 7
    assert result['retries'] == 8  # Seven retained requests plus a second target retry.
    assert result['point'] == point
