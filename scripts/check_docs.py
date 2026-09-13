#!/usr/bin/env python3
# Read-only: no fixes, network, database files, or bytecode writes.
# ADR commits still require --no-verify; the tracked hook blocks decisions/.
"""Check repository documentation against files and shipped code.

Checks cover local Markdown navigation, ADR markers/explicit acceptance claims,
Constitution numbering, quoted hash expressions, legacy SQL, fenced blocks,
README's file map, and serialization compatibility samples. Hash expressions
are compared structurally with the shipped helper ASTs, never evaluated as code.
SQL is compared only in memory. Serialization samples are regression examples,
not an implementation of Proposed ADR 0027's parser or cryptographic protocol.

Natural-language authority claims cannot be proved by a Markdown checker.
Unclassified Proposed references, non-executable formulas and unsupported markup
are reported as unchecked. Task-specific diff-scope reviews and general semantic
contradiction audits still require a human; this is not ratification clearance.
"""

import argparse
import ast
from collections import Counter
from contextlib import closing
import html
import json
from pathlib import Path
import re
import runpy
import sqlite3
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ARCH = 'spec/NYX_ARCHITECTURE.md'
V0 = 'spec/NYX_V0_IMPLEMENTATION.md'
CHECKS = ('links', 'adr_markers', 'proposed_references', 'invariants',
          'hash_formulas', 'legacy_schema', 'fences', 'readme_map', 'serialization')


class Report:
    def __init__(self):
        self.failures = []
        self.unchecked = []
        self.checked = Counter({name: 0 for name in CHECKS})

    def add(self, check, path, line, message, *, unchecked=False):
        item = dict(check=check, path=str(path), line=line, message=message)
        target = self.unchecked if unchecked else self.failures
        if item not in target:
            target.append(item)

    def result(self):
        key = lambda item: (item['path'], item['line'], item['check'], item['message'])
        return dict(ok=not self.failures, checked=dict(self.checked),
                    failures=sorted(self.failures, key=key),
                    unchecked=sorted(self.unchecked, key=key))


def plain(text):
    return re.sub(r'[*_`]', '', text)


def slug(text):
    text = re.sub(r'!?\[([^]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\[([^]]+)\]\[[^]]*\]', r'\1', text)
    text = re.sub(r'(?<!\w)_{1,2}([^_]+)_{1,2}(?!\w)', r'\1', text)
    text = html.unescape(re.sub(r'<[^>]*>', '', text)).lower().strip()
    # GitHub-style heading IDs: retain letters, marks, numbers, hyphens,
    # underscores and spaces; discard punctuation/symbols. Do not normalize.
    text = text.replace('`', '').replace('*', '')
    return ''.join(c for c in text if c in '-_ ' or
                   unicodedata.category(c)[0] in 'LMN').replace(' ', '-')


def document(text, path, report):
    """Mask fenced/inline code for navigation without losing source positions."""
    lines = text.splitlines(keepends=True)
    visible = []
    fence = None
    for number, line in enumerate(lines, 1):
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*?)[\r\n]*$', line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
                report.checked['fences'] += 1
            visible.append('\n' if line.endswith('\n') else '')
        elif match:
            fence = (match[1][0], len(match[1]), number)
            if not match[2].strip():
                report.add('fences', path, number, 'Code fence has no language tag')
            visible.append('\n' if line.endswith('\n') else '')
        else:
            visible.append(line)
            if re.match(r'^\s*(?:>|[-+*] )\s*(`{3,}|~{3,})', line):
                report.add('fences', path, number, 'Container-nested fence needs manual validation', unchecked=True)
    if fence:
        report.add('fences', path, fence[2], 'Unclosed code fence')
    body = ''.join(visible)
    anchors = set()
    for index, line in enumerate(visible):
        heading = re.match(r'^ {0,3}#{1,6}\s+(.+?)(?:\s+#+\s*)?$', line.rstrip())
        title = heading[1] if heading else None
        if index + 1 < len(visible) and line.strip() and re.fullmatch(r' {0,3}(?:=+|-+)\s*', visible[index + 1]):
            title = line.strip()
        if title is not None:
            base = slug(title)
            name, suffix = base, 0
            while name in anchors:
                suffix += 1
                name = f'{base}-{suffix}'
            anchors.add(name)
    anchors.update(re.findall(r'<a\b[^>]*\b(?:id|name)=["\x27]([^"\x27]+)', body, re.I))
    # Inline code can contain Markdown-looking examples, which aren't links.
    body = re.sub(r'(`+)([\s\S]*?)(?<!`)\1(?!`)',
                  lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]), body)
    return body, anchors


def links(body, path, report):
    """Inline, full/collapsed reference and defined shortcut links, plus images.

    Bare undefined [words] are ordinary Markdown, not broken shortcut links.
    Balanced parentheses and angle-delimited destinations are supported.
    """
    definitions = {}
    definition_spans = []
    for m in re.finditer(r'^ {0,3}\[([^]\n]+)\]:\s*(<[^>\n]*>|\S+)(?:[^\n]*)', body, re.M):
        definitions[' '.join(m[1].lower().split())] = m[2].strip('<>')
        definition_spans.append(m.span())
    found = []
    i = 0
    while i < len(body):
        if body[i] != '[' or (i and body[i - 1] == '\\') or any(a <= i < b for a, b in definition_spans):
            i += 1
            continue
        start = i
        end = body.find(']', i + 1)
        if end < 0:
            break
        label = body[i + 1:end]
        i = end + 1
        number = body.count('\n', 0, start) + 1
        if '[' in label:
            report.add('links', path, number, 'Nested link label needs manual validation', unchecked=True)
            continue
        if body[i:i + 1] == '(':
            j, depth, angle, escaped = i + 1, 1, False, False
            while j < len(body) and depth:
                c = body[j]
                if not escaped:
                    if c == '<':
                        angle = True
                    elif c == '>':
                        angle = False
                    elif not angle and c == '(':
                        depth += 1
                    elif not angle and c == ')':
                        depth -= 1
                escaped = c == '\\' and not escaped
                j += 1
            if depth:
                report.add('links', path, number, 'Unclosed inline link destination')
                continue
            destination = body[i + 1:j - 1].strip()
            if destination.startswith('<'):
                destination = destination[1:destination.find('>')]
            else:
                destination = re.split(r'\s+["\x27]', destination, maxsplit=1)[0]
            found.append((number, html.unescape(re.sub(r'\\([()])', r'\1', destination))))
            i = j
        else:
            explicit = body[i:i + 1] == '['
            key = label
            if explicit:
                closing = body.find(']', i + 1)
                if closing < 0:
                    report.add('links', path, number, 'Unclosed reference link')
                    continue
                key = body[i + 1:closing] or label
                i = closing + 1
            key = ' '.join(key.lower().split())
            if key in definitions:
                found.append((number, definitions[key]))
            elif explicit:
                report.add('links', path, number, f'Undefined link reference: {key}')
    # Validate even unused local definitions; they are maintained navigation.
    for a, _ in definition_spans:
        m = re.match(r' {0,3}\[([^]]+)\]', body[a:])
        found.append((body.count('\n', 0, a) + 1, definitions[' '.join(m[1].lower().split())]))
    return found


def check_navigation(root, docs, parsed, report):
    for path, (body, _) in parsed.items():
        for number, destination in links(body, path, report):
            try:
                url = urlsplit(destination)
            except ValueError as error:
                report.add('links', path, number, f'Invalid link destination {destination}: {error}')
                continue
            if url.scheme or url.netloc:
                continue  # No network access, even for validation.
            local = unquote(url.path)
            target = ((root / local.lstrip('/')) if local.startswith('/') else
                      (root / path).parent / local) if local else root / path
            target = target.resolve()
            if not target.exists():
                report.add('links', path, number, f'Missing local target: {destination}')
                continue
            report.checked['links'] += 1
            if url.fragment:
                if not target.is_file() or target.suffix.lower() != '.md':
                    report.add('links', path, number, f'Non-Markdown fragment needs manual validation: {destination}', unchecked=True)
                    continue
                relative = target.relative_to(root).as_posix() if target.is_relative_to(root) else str(target)
                if relative not in parsed:
                    parsed_target = document(target.read_text(encoding='utf-8'), relative, report)
                else:
                    parsed_target = parsed[relative]
                if unquote(url.fragment) not in parsed_target[1]:
                    report.add('links', path, number, f'Missing heading/anchor: {destination}')
    readme = docs.get('README.md', '')
    match = re.search(r'^## Decision-to-code map\s*\n([\s\S]*?)(?=^## |\Z)', readme, re.M)
    if not match:
        report.add('readme_map', 'README.md', 1, 'Missing decision-to-code map')
        return
    # Links are checked above; also check unlinked file paths (not symbol names).
    body, _ = parsed['README.md']
    map_start = readme.count('\n', 0, match.start()) + 1
    map_end = map_start + match[0].count('\n')
    for number, destination in links(body, 'README.md', report):
        if map_start <= number <= map_end:
            url = urlsplit(destination)
            if not url.scheme and not url.netloc:
                report.checked['readme_map'] += 1
                if not (root / unquote(url.path)).is_file():
                    report.add('readme_map', 'README.md', number, f'Map file does not exist: {destination}')
    for m in re.finditer(r'`([^`\n]+)`', match[0]):
        candidate = m[1]
        if re.fullmatch(r'[\w./-]+\.(?:py|sql|json|md|toml)', candidate):
            report.checked['readme_map'] += 1
            if not (root / candidate).is_file():
                report.add('readme_map', 'README.md', map_start + match[0].count('\n', 0, m.start()), f'Map file does not exist: {candidate}')


def check_authority(docs, parsed, report):
    proposed = set()
    for path, (body, _) in parsed.items():
        if not re.fullmatch(r'decisions/\d{4}-[^/]+\.md', path):
            continue
        fields = {}
        for field in ('Status', 'Implementation'):
            markers = re.findall(rf'^\s*(?:-\s+)?{field}:\s*(\S[^\n]*)', plain(body), re.M | re.I)
            if len(markers) != 1:
                report.add('adr_markers', path, 1, f'Expected one {field} marker; found {len(markers)}')
            else:
                fields[field] = markers[0]
                report.checked['adr_markers'] += 1
                if field == 'Status' and markers[0].lower().startswith('proposed'):
                    proposed.add(Path(path).name[:4])
        if Path(path).name[:4] in proposed:
            if 'Implementation' in fields and not re.match(r'None\b', fields['Implementation']):
                report.add('adr_markers', path, 1, 'Proposed ADR must retain Implementation: None')
    for path, body in docs.items():
        # Classify explicit nearby status assertions, not whole paragraphs using
        # "accepted" for some unrelated decision. Everything else stays unchecked.
        for number, line in enumerate(body.splitlines(), 1):
            def reference_label(match):
                target = re.search(r'(\d{4})-[^/]+\.md', match[2])
                return f'ADR {target[1]}' if target else match[1]

            readable = plain(re.sub(r'\[([^]]+)\]\(([^)]*)\)', reference_label, line))
            for adr in sorted(proposed):
                refs = list(re.finditer(rf'\bADR\s+{adr}\b', readable, re.I))
                linked = re.search(rf'\b{adr}-[^\s)]+\.md', line)
                if not refs and not linked:
                    continue
                checked = False
                for ref in refs:
                    before, after = readable[:ref.start()], readable[ref.end():]
                    positive_before = re.search(r'\b(?:accepted|ratified)(?:\s+(?:decision|boundary))?\s*:?\s*$', before, re.I)
                    conditional = re.search(r'\b(?:not|if|once|when)\b[^.;]*$', before, re.I)
                    positive_after = re.match(r'\s*(?:(?:is|was|has been)\s+|[|:(]\s*)(?:accepted|ratified)\b', after, re.I)
                    if not conditional and (positive_before or positive_after):
                        report.add('proposed_references', path, number, f'Proposed ADR {adr} explicitly described as accepted/ratified')
                        checked = True
                    elif re.search(r'\b(?:proposed|unratified|draft)\s*:?\s*$', before, re.I) or re.match(r'\s+(?:(?:is|remains|is still)\s+)?(?:proposed|unratified|draft)\b', after, re.I):
                        checked = True
                if checked:
                    report.checked['proposed_references'] += 1
                else:
                    report.add('proposed_references', path, number, f'ADR {adr} reference requires human authority/context review', unchecked=True)


def check_invariants(docs, report):
    text = docs.get(ARCH, '')
    section = re.search(r'^## Constitution[^\n]*\n([\s\S]*?)(?=^## |\Z)', text, re.M)
    numbers = re.findall(r'^(\d+)\.\s+', section[1], re.M) if section else []
    if not numbers or list(map(int, numbers)) != list(range(1, len(numbers) + 1)):
        report.add('invariants', ARCH, 1, f'Expected contiguous, unique invariants starting at 1; found {numbers}')
    else:
        report.checked['invariants'] += len(numbers)


class Unsupported(ValueError):
    pass


class HashContract:
    """Small symbolic interpreter for the actual pure hashing helper bodies."""
    def __init__(self, source):
        tree = ast.parse(source)
        self.functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        self.constants = {n.targets[0].id: n.value for n in tree.body
                          if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}

    def call(self, name, args):
        function = self.functions[name]
        body = [n for n in function.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        if len(body) != 1 or not isinstance(body[0], ast.Return):
            raise Unsupported(f'Unsupported helper body: {name}')
        return self.symbol(body[0].value, dict(zip((p.arg for p in function.args.args), args)))

    def symbol(self, node, values=None):
        values = values or {}
        if isinstance(node, ast.Constant):
            return ('literal', node.value)
        if isinstance(node, ast.Name):
            if node.id in values:
                return values[node.id]
            if node.id in self.constants:
                return self.symbol(self.constants[node.id])
            return ('variable', node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            parts = [self.symbol(node.left, values), self.symbol(node.right, values)]
            return ('concat', *(p for part in parts for p in (part[1:] if part[0] == 'concat' else (part,))))
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            return ('or', *(self.symbol(n, values) for n in node.values))
        if isinstance(node, (ast.List, ast.Tuple)):
            return ('list', *(self.symbol(n, values) for n in node.elts))
        if isinstance(node, ast.Call) and not node.keywords:
            args = [self.symbol(n, values) for n in node.args]
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in ('canonical_json', 'sorted', 'SHA256', 'UTF8'):
                    return (name, *args)
                if name in self.functions:
                    return self.call(name, args)
            if isinstance(node.func, ast.Attribute):
                owner, method = node.func.value, node.func.attr
                if method == 'join' and len(args) == 1 and args[0][0] == 'list':
                    sep = self.symbol(owner, values)
                    items = args[0][1:]
                    return ('concat', *(p for i, item in enumerate(items) for p in ((sep, item) if i else (item,))))
                if method == 'encode' and args == [('literal', 'utf-8')]:
                    return ('UTF8', self.symbol(owner, values))
                if method == 'hexdigest' and not args and isinstance(owner, ast.Call) and ast.unparse(owner.func) == 'hashlib.sha256':
                    return ('SHA256', self.symbol(owner.args[0], values))
        raise Unsupported(f'Unsupported expression: {ast.unparse(node)}')


def check_hashes(root, docs, report):
    source = (root / 'src/nyx/hashing.py').read_text(encoding='utf-8')
    contract = HashContract(source)
    expected = {}
    names = {'idempotency_key': ('source_id', 'occurred_at', 'payload'),
             'event_hash': ('event_minus_hash_fields', 'prev_event_hash'),
             'dep_hash': ('dependency_event_hashes',)}
    for name, parameters in names.items():
        try:
            expected[name] = contract.call(name, [('variable', p) for p in parameters])
        except (Unsupported, KeyError) as error:
            report.add('hash_formulas', 'src/nyx/hashing.py', 1, str(error), unchecked=True)
    # Read the actual legacy fold expression and its genesis assignment, too.
    projection = ast.parse((root / 'src/nyx/projection.py').read_text(encoding='utf-8'))
    assignments = {n.targets[0].id: n.value for n in ast.walk(projection)
                   if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    try:
        prior = assignments['prior_hash']
        if not isinstance(prior, ast.IfExp) or ast.unparse(prior.test) != 'prior_view is None':
            raise Unsupported('Legacy genesis selection changed; review required')
        seed = ast.literal_eval(assignments[prior.body.id])
        expression = ast.unparse(assignments['new_view_hash']).replace('hashing._sha256_hex', '_sha256_hex').replace('envelope.event_hash', 'event_hash')
        expected['genesis'] = contract.symbol(ast.parse(expression, mode='eval').body,
                                              {'prior_hash': ('literal', seed)})
    except (KeyError, AttributeError, ValueError) as error:
        report.add('hash_formulas', 'src/nyx/projection.py', 1, f'Genesis expression unchecked: {error}', unchecked=True)
    seen = set()
    for path, text in docs.items():
        if not path.startswith('spec/'):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for start in re.finditer(r'\bSHA256\(', line):
                depth, end = 1, start.end()
                while end < len(line) and depth:
                    depth += (line[end] == '(') - (line[end] == ')')
                    end += 1
                expression = line[start.start():end]
                try:
                    node = ast.parse(expression, mode='eval').body
                    variables = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                    name = ('idempotency_key' if 'source_id' in variables else
                            'event_hash' if 'event_minus_hash_fields' in variables else
                            'dep_hash' if 'dependency_event_hashes' in variables else
                            'genesis' if variables <= {'SHA256', 'UTF8', 'event_hash'} and 'event_hash' in variables else None)
                    if name not in expected:
                        raise Unsupported('No exact shipped helper binding')
                    actual = contract.symbol(node)
                    seen.add(name)
                    report.checked['hash_formulas'] += 1
                    if actual != expected[name]:
                        report.add('hash_formulas', path, number, f'{name} formula differs from shipped code: {expression}')
                except (SyntaxError, Unsupported) as error:
                    report.add('hash_formulas', path, number, f'Unchecked formula {expression}: {error}', unchecked=True)
    for name in expected.keys() - seen:
        report.add('hash_formulas', 'spec/', 1, f'No supported quoted {name} formula; prose not compared', unchecked=True)
    report.add('hash_formulas', 'spec/', 1, 'Hash/serialization prose and formulas outside the supported SHA256 expression syntax require semantic review', unchecked=True)


def table_signature(sql):
    # Isolate just this CREATE statement, excluding comments. Never run the rest
    # of a doc fence or schema (which might contain pragmas, ATTACH, or DML).
    clean = re.sub(r'--[^\n]*|/\*[\s\S]*?\*/', '', sql)
    matches = list(re.finditer(r'\bCREATE\s+TABLE\s+resolved_beliefs\s*\(', clean, re.I))
    if len(matches) != 1:
        raise ValueError(f'Expected one resolved_beliefs CREATE; found {len(matches)}')
    start = matches[0].start()
    end = clean.find(';', matches[0].end())
    if end < 0:
        raise ValueError('Unterminated resolved_beliefs CREATE')
    ddl = clean[start:end + 1]
    with closing(sqlite3.connect(':memory:')) as conn:
        conn.execute(ddl)
        columns = conn.execute('PRAGMA table_info(resolved_beliefs)').fetchall()
        # Compare tokens as well: PRAGMA alone misses CHECK, UNIQUE, FK and
        # table-level clauses. Whitespace/comments/case outside literals differ
        # legitimately between the mechanical excerpt and shipped DDL.
        tokens = re.findall(r"'(?:''|[^'])*'|\w+|[^\s]", ddl)
        tokens = tuple(t if t.startswith("'") else t.lower() for t in tokens)
        return columns, tokens


def check_schema(root, docs, report):
    try:
        source = table_signature((root / 'schema.sql').read_text(encoding='utf-8'))
        excerpt = table_signature('\n'.join(re.findall(r'```sql\s*\n([\s\S]*?)\n```', docs.get(V0, ''))))
        report.checked['legacy_schema'] += 1
        if source != excerpt:
            report.add('legacy_schema', V0, 1, 'resolved_beliefs columns/constraints differ from schema.sql')
    except (ValueError, sqlite3.Error) as error:
        report.add('legacy_schema', V0, 1, str(error))


def check_serialization(root, report):
    helpers = runpy.run_path(str(root / 'src/nyx/hashing.py'))
    samples = [({'z': None, 'a': ['snow', 1, True]}, '{"a":["snow",1,true],"z":null}'),
               ({'\U00010000': 1, '\ue000': 2}, '{"\ue000":2,"\U00010000":1}'),
               ('\b\t\n\f\r\x00/\u2028', '"\\b\\t\\n\\f\\r\\u0000/\u2028"'),
               ({'n': 1.0, 'i': 1}, '{"i":1,"n":1.0}')]
    for index, (value, expected) in enumerate(samples, 1):
        report.checked['serialization'] += 1
        if helpers['canonical_json'](value).encode('utf-8') != expected.encode('utf-8'):
            report.add('serialization', 'src/nyx/hashing.py', 1, f'Canonical JSON compatibility sample {index} differs')
    report.checked['serialization'] += 1
    if helpers['canonical_set']([{'b': 2}, {'a': 1}, {'b': 2}]) != [{'a': 1}, {'b': 2}]:
        report.add('serialization', 'src/nyx/hashing.py', 1, 'Canonical set ordering/deduplication sample differs')
    report.add('serialization', 'src/nyx/hashing.py', 1, 'Finite compatibility samples only; no Proposed wire/parser/crypto conformance or exhaustive number-format proof', unchecked=True)


def check_repository(root=ROOT):
    root = Path(root).resolve()
    report = Report()
    paths = [root / 'README.md', root / 'GAPS.md']
    for directory in ('spec', 'decisions', 'design'):
        paths.extend(sorted((root / directory).rglob('*.md')))
    docs = {}
    for path in paths:
        try:
            docs[path.relative_to(root).as_posix()] = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as error:
            report.add('links', path.relative_to(root), 1, str(error))
    parsed = {p: document(t, p, report) for p, t in docs.items()}
    for check, operation in (
        ('links', lambda: check_navigation(root, docs, parsed, report)),
        ('adr_markers', lambda: check_authority(docs, parsed, report)),
        ('invariants', lambda: check_invariants(docs, report)),
        ('hash_formulas', lambda: check_hashes(root, docs, report)),
        ('legacy_schema', lambda: check_schema(root, docs, report)),
        ('serialization', lambda: check_serialization(root, report)),
    ):
        try:
            operation()
        except (OSError, UnicodeError, SyntaxError, ValueError, KeyError) as error:
            report.add(check, '.', 1, f'Check could not run: {error}')
    return report.result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--fix-none', action='store_true', default=True,
                        help='Read only (default and only mode)')
    parser.add_argument('--json', action='store_true', help='Emit structured results')
    args = parser.parse_args(argv)
    result = check_repository()
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        for category in ('failures', 'unchecked'):
            for item in result[category]:
                print(f"{category.upper()} {item['path']}:{item['line']} [{item['check']}] {item['message']}")
        print(f"{len(result['failures'])} failures; {len(result['unchecked'])} unchecked findings")
        print('Checked: ' + ', '.join(f'{k}={v}' for k, v in result['checked'].items()))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
