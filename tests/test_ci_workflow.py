"""The workflow uses JSON, a YAML 1.2 subset, for stdlib-only validation."""
import json
from pathlib import Path


def test_windows_ci_contract():
    workflow = json.loads((Path(__file__).resolve().parents[1] /
                           '.github/workflows/ci.yml').read_text(encoding='utf-8'))
    assert workflow['on'] == {'pull_request': {}, 'push': {'branches': ['main']}}
    job = workflow['jobs']['test']
    assert job['runs-on'] == 'windows-latest'
    steps = job['steps']
    assert steps[0]['uses'].startswith('actions/checkout@')
    assert steps[1]['uses'].startswith('actions/setup-python@')
    assert steps[1]['with']['python-version'] == '3.14'
    assert steps[2]['run'] == 'python -m pip install -e .[dev]'
    assert '--basetemp=$t' in steps[3]['run']
    assert '$env:RUNNER_TEMP' in steps[3]['run']
    assert "PYTHONDONTWRITEBYTECODE='1'" in steps[3]['run']
    assert '-p no:cacheprovider' in steps[3]['run']
    assert steps[4]['run'] == 'python -B scripts/check_docs.py --fix-none'
    assert not any('node' in step.get('uses', '').lower() for step in steps)
