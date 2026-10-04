"""Literal bytes, ratified value boundaries, and the frozen 92-revision survey."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def extract(data):
    from nyx.adr_literals import extract_literals
    return extract_literals(data)


@pytest.mark.parametrize('newline', [b'\n', b'\r\n', b'\r'])
def test_exact_spans_internal_endings_and_metadata_boundary(newline):
    data = newline.join([b'# ADR literal ##', b'', 'Status: Accep\u00e9d'.encode(),
        b'continuation', b'- **Date:** 2026', b'- **Scope:** example', b'',
        b'Implementation: None', b'## Heading'])
    result = extract(data)
    assert [r['property_id'] for r in result] == ['adr.title.literal', 'adr.status.literal', 'adr.implementation.literal']
    assert result[0]['value'] == 'ADR literal ##'
    assert result[1]['value'] == 'Accep\u00e9d' + newline.decode() + 'continuation'
    assert result[1]['location']['start_line'] == 3
    assert result[1]['location']['end_line'] == 4
    for field in result:
        loc = field['location']
        assert data[loc['start_byte']:loc['end_byte']].decode('utf-8') == field['value']
        assert '- **' not in field['value']


@pytest.mark.parametrize('prefix,property_id', [('Status: ', 'adr.status.literal'),
    ('- **Status:** ', 'adr.status.literal'), ('Implementation: ', 'adr.implementation.literal'),
    ('- **Implementation:** ', 'adr.implementation.literal')])
def test_four_exact_prefixes(prefix, property_id):
    assert extract((prefix + 'Literal\n- unrelated\n').encode())[0]['value'] == 'Literal'
    assert extract((prefix + 'Literal\n').encode())[0]['property_id'] == property_id


@pytest.mark.parametrize('bad', [b'\xef\xbb\xbf# Title', b'\xff', b'```\nStatus: X\n',
    b'~~~\n# Title\n', b'Status: \n', b'# \n', b'Implementation: ',
    b'Status: One\n\nStatus: Two\n', b'# One\n\n# Two\n',
    b'Implementation: One\n\n- **Implementation:** Two',
    b'**Status**: X', b'Status:X', b'- Status: X', b'**Implementation:** X',
    b'- **Status**: X', b'Status: X\nImplementation: Y\n'])
def test_artifact_refusal(bad):
    from nyx.adr_literals import LiteralExtractionError
    with pytest.raises(LiteralExtractionError): extract(bad)


def test_excluded_examples_missing_fields_and_keyword_prose():
    data = b'''Status includes the explicit partial-supersession notice.
Implementation is separate work.
> Status: quoted
    Implementation: indented
```python
# Fenced
Status: fake
````
~~~
Implementation: fake
~~~
'''
    assert extract(data) == []
    assert extract(b'# Real\n\n' + data)[0]['value'] == 'Real'


def test_whitespace_and_unicode_are_preserved():
    assert extract('Status:  e\u0301  \n'.encode())[0]['value'] == ' e\u0301  '


def test_pinned_history_survey_all_extract_zero_refused():
    if shutil.which('git') is None: pytest.skip('Git absent: pinned blob corpus survey requires local git cat-file; no network')
    fixture = json.loads((ROOT / 'tests/fixtures/adr_reports/survey.json').read_bytes())
    assert fixture['baseline'] == 'a30e94acf0ef86f881a7d68b9d950aa3a6740656'
    assert len(fixture['revisions']) == 92
    count = 0
    missing = {}
    for revision in fixture['revisions']:
        blob = revision['blob']
        data = subprocess.run(['git', 'cat-file', 'blob', blob], cwd=ROOT,
                              capture_output=True, check=True).stdout
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
        result = extract(data)
        count += len(result)
        for field in result:
            assert not any(line.startswith('- **') for line in field['value'].splitlines())
    assert count == 253
