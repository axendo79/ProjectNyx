"""Only tiny smoke coverage; full scaling samples are run manually."""

import json
from pathlib import Path
import subprocess
import sys


def test_store_probe_executes(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts/probe_store_scaling.py'
    output = tmp_path / 'result.json'
    result = subprocess.run([sys.executable, '-B', str(script), '--sizes', '6', '12',
                             '--projector-1-max-events', '6', '--json', str(output)],
                            cwd=tmp_path, capture_output=True, text=True, check=True)
    report = json.loads(output.read_text(encoding='utf-8'))
    assert [(r['projector_version'], r['events']) for r in report['samples']] == [
        ('1', 6), ('2', 6), ('2', 12)]
    assert report['skipped'][0]['events'] == 12
    assert 'SKIPPED' in result.stdout
    for row in report['samples']:
        assert row['verified'] and row['file_bytes_per_event'] > 0
        assert row['subjects'] * 6 == row['events']
        assert (row['committed_nodes'] > 0) == (row['projector_version'] == '2')
        assert row['content_bytes_per_event'] == row['node_content_bytes'] / row['events']
