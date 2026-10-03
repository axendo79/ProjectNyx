"""Independent evidence for a subset of the accepted canonical JSON domain.

No float/private codec, parser policy or production hash representation changes.
ADRs 0014 section 6 and 0025 section 2 govern the existing canonical bytes.
"""

import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess

import pytest

from nyx import hashing


TEXT = ["", "ascii", "\u00e9", "e\u0301", "\u96ea", "\U0001f600", "\ue000",
        "\u2028\u2029", '"\\/', "\b\f\n\r\t", "".join(map(chr, range(32)))]
KEYS = TEXT + ["10", "2", "__proto__", "constructor"]
LIMIT = 2**53 - 1  # Evidence subset shared with exact JavaScript integers.


def independent_canonical(value):
    """Test-only encoder; no production utility or Python JSON encoder calls.

    Evidence covers null/bools, exact safe integers, Unicode scalar strings,
    lists and string-keyed objects. Other types remain outside this oracle.
    """
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int and -LIMIT <= value <= LIMIT:
        return str(value)
    if type(value) is str:
        escapes = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
                   "\n": "\\n", "\r": "\\r", "\t": "\\t"}
        chars = []
        for char in value:
            if 0xD800 <= ord(char) <= 0xDFFF:
                raise ValueError("surrogates are outside the evidence subset")
            chars.append(escapes.get(char, f"\\u{ord(char):04x}" if ord(char) < 32 else char))
        return '"' + "".join(chars) + '"'
    if type(value) is list:
        return "[" + ",".join(independent_canonical(item) for item in value) + "]"
    if type(value) is dict and all(type(key) is str for key in value):
        return "{" + ",".join(independent_canonical(key) + ":" + independent_canonical(value[key])
                              for key in sorted(value)) + "}"
    raise ValueError("value is outside the evidence subset")


def payloads(seed):
    rng = random.Random(seed)

    def value(depth):
        kind = rng.randrange(6 if depth else 4)
        if kind == 0:
            return None
        if kind == 1:
            return bool(rng.randrange(2))
        if kind == 2:
            return rng.choice([-LIMIT, -1, 0, 1, LIMIT, rng.randrange(-100000, 100000)])
        if kind == 3:
            return rng.choice(TEXT)
        if kind == 4:
            return [value(depth - 1) for _ in range(rng.randrange(5))]
        return {key: value(depth - 1) for key in rng.sample(KEYS, rng.randrange(5))}

    return [{"\U0001f600": False, "\ue000": "\u00e9", "2": -1, "10": 0},
            {"\u00e9": 1, "e\u0301": 2}, TEXT,
            *[value(4) for _ in range(200)]]


def test_independent_oracle_known_bytes():
    vectors = [
        (None, "null"), (True, "true"), (False, "false"),
        ([2, 1, 2], "[2,1,2]"),
        ("\x00\b\f\n\r\t\x1f", r'"\u0000\b\f\n\r\t\u001f"'),
        ({"\u00e9": 1, "e\u0301": 2}, '{"e\u0301":2,"\u00e9":1}'),
        ({"\U0001f600": False, "\ue000": "\u00e9", "2": -1, "10": 0},
         '{"10":0,"2":-1,"\ue000":"\u00e9","\U0001f600":false}'),
    ]
    for value, expected in vectors:
        assert independent_canonical(value).encode("utf-8") == expected.encode("utf-8")


def test_oracle_does_not_consult_shared_serializer(monkeypatch):
    monkeypatch.setattr(hashing, "canonical_json", lambda _: '"shared-serializer-defect"')
    monkeypatch.setattr(json, "dumps", lambda *args, **kwargs: '"shared-encoder-defect"')
    assert independent_canonical({"x": "\u96ea", "n": 1}) == '{"n":1,"x":"\u96ea"}'


@pytest.mark.parametrize("seed", [0, 1729, 20261003])
def test_generated_payload_bytes_and_hashes_match_independent_oracle(seed):
    for value in payloads(seed):
        expected = independent_canonical(value)
        assert hashing.canonical_json(value).encode("utf-8") == expected.encode("utf-8")
        assert hashing._sha256_hex(hashing.canonical_json(value)) == hashlib.sha256(
            expected.encode("utf-8")).hexdigest()


def test_node_bytes_and_hashes_match_independent_python_oracle():
    node = shutil.which("node")
    if node is None:
        pytest.skip("optional cross-language evidence requires Node.js")
    values = [value for seed in (0, 1729, 20261003) for value in payloads(seed)]
    script = Path(__file__).parent / "fixtures/canonical_subset.js"
    result = subprocess.run([node, str(script)], input=json.dumps(values, ensure_ascii=True),
                            capture_output=True, text=True, encoding="utf-8", check=True)
    actual = json.loads(result.stdout)
    assert len(actual) == len(values)
    for value, row in zip(values, actual):
        expected = independent_canonical(value)
        assert row["canonical"].encode("utf-8") == expected.encode("utf-8")
        assert row["canonical"] == hashing.canonical_json(value)
        assert row["sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
