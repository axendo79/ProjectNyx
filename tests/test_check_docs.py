"""Documentation checks use isolated fixtures; the real docs need not be clean."""

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
checker = runpy.run_path(str(ROOT / 'scripts/check_docs.py'))


@pytest.fixture
def tree(tmp_path):
    for directory in ('spec', 'decisions', 'design', 'src/nyx', 'tests'):
        (tmp_path / directory).mkdir(parents=True)
    for path in ('src/nyx/hashing.py', 'src/nyx/projection.py', 'schema.sql'):
        shutil.copyfile(ROOT / path, tmp_path / path)
    (tmp_path / 'README.md').write_text(
        '# Fixture\n\n[Architecture](spec/NYX_ARCHITECTURE.md#constitution-invariants)\n'
        '[helper][hash]\n\n## Decision-to-code map\n\n'
        '| ADR | Code | Tests |\n|---|---|---|\n'
        '| [0001](decisions/0001-test.md) | [hash] | [test](tests/test_example.py) |\n'
        '\n[hash]: src/nyx/hashing.py\n', encoding='utf-8')
    (tmp_path / 'GAPS.md').write_text('# Gaps\n', encoding='utf-8')
    (tmp_path / 'tests/test_example.py').write_text('# fixture\n', encoding='utf-8')
    (tmp_path / 'decisions/0001-test.md').write_text(
        '# 0001\n\nStatus: Accepted\n\nImplementation: Implemented\n', encoding='utf-8')
    (tmp_path / 'decisions/0027-test.md').write_text(
        '# 0027\n\nStatus: Proposed\n\nImplementation: None\n', encoding='utf-8')
    (tmp_path / 'spec/NYX_ARCHITECTURE.md').write_text(
        '# Architecture\n\n## Constitution (invariants)\n\n'
        '1. **First.** Text.\n2. **Second.** Text.\n\n## Next\n', encoding='utf-8')
    # Use the real excerpt/formulas, with language tags so the fixture isolates
    # each check from the current tree's outstanding documentation findings.
    spec = (ROOT / 'spec/NYX_V0_IMPLEMENTATION.md').read_text(encoding='utf-8')
    import re
    sql = re.search(r'CREATE TABLE resolved_beliefs \([\s\S]*?\n\);', spec)[0]
    formulas = []
    for line in spec.splitlines():
        if ('SHA256(' in line and not line.strip().startswith('--')):
            formulas.append(line)
    (tmp_path / 'spec/NYX_V0_IMPLEMENTATION.md').write_text(
        '# V0\n\n```text\n' + '\n'.join(formulas) + '\n```\n\n```sql\n' + sql + '\n```\n', encoding='utf-8')
    return tmp_path


def edit(tree, path, old, new):
    target = tree / path
    text = target.read_text(encoding='utf-8')
    assert old in text
    target.write_text(text.replace(old, new), encoding='utf-8')


def result(tree):
    return checker['check_repository'](tree)


def failures(tree, check):
    return [f for f in result(tree)['failures'] if f['check'] == check]


def test_all_checks_have_passing_case_and_are_read_only(tree):
    before = {p.relative_to(tree): p.read_bytes() for p in tree.rglob('*') if p.is_file()}
    report = result(tree)
    assert report['failures'] == []
    assert all(report['checked'][key] for key in checker['CHECKS'] if key != 'proposed_references')
    after = {p.relative_to(tree): p.read_bytes() for p in tree.rglob('*') if p.is_file()}
    assert before == after


@pytest.mark.parametrize('destination', ['missing.md', 'spec/NYX_ARCHITECTURE.md#missing'])
def test_links_missing_file_and_anchor(tree, destination):
    edit(tree, 'GAPS.md', '# Gaps', f'# Gaps\n\n[broken]({destination})')
    assert failures(tree, 'links')


def test_reference_links_images_encoded_paths_and_duplicate_headings(tree):
    (tree / 'design/a file(test).md').write_text(
        '# Hello, `world`!\n## Hello, world!\n## Hello, world!-1\n'
        '\nSetext title\n============\n\n<a id="explicit"></a>\n', encoding='utf-8')
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n'
         '[inline](design/a%20file(test).md#hello-world)\n'
         '[angle](<design/a file(test).md#hello-world-1>)\n'
         '[ref][target]\n[target]: design/a%20file(test).md#hello-world-1-1\n'
         '[collapsed][]\n[collapsed]: design/a%20file(test).md#setext-title\n'
         '![image](tests/test_example.py)\n'
         '[html](design/a%20file(test).md#explicit)\n'
         '`[ignored](missing.md)`\n```text\n[ignored](missing.md)\n```\n')
    assert failures(tree, 'links') == []
    edit(tree, 'GAPS.md', '[ref][target]', '[ref][absent]')
    assert any('Undefined link reference' in f['message'] for f in failures(tree, 'links'))


def test_external_links_are_never_fetched_and_fragments_are_unchecked(tree):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n[x](https://invalid.invalid)\n'
         '[y](mailto:nobody@example.invalid)\n[z](schema.sql#L1)\n')
    report = result(tree)
    assert report['failures'] == []
    assert any('Non-Markdown fragment' in f['message'] for f in report['unchecked'])


@pytest.mark.parametrize('field', ['Status', 'Implementation'])
def test_missing_adr_markers(tree, field):
    edit(tree, 'decisions/0001-test.md', field + ':', 'Missing:')
    assert any(field in f['message'] for f in failures(tree, 'adr_markers'))


def test_bold_markers(tree):
    edit(tree, 'decisions/0001-test.md', 'Status: Accepted', '- **Status:** Accepted')
    edit(tree, 'decisions/0001-test.md', 'Implementation: Implemented', '- **Implementation:** Implemented')
    assert not failures(tree, 'adr_markers')


@pytest.mark.parametrize('bold', [False, True])
def test_status_header_formats_and_literal_values(tree, bold):
    status = 'Accepted as an **INTERIM STANCE**. Body says Proposed.'
    implementation = '`src/nyx/hashing.py` implements ' + 'x' * 120
    status_prefix = '- **Status:** ' if bold else 'Status: '
    (tree / 'decisions/0001-test.md').write_text(
        '# Fixture title\n\n' + status_prefix + status + '\n\n'
        + 'Implementation: ' + implementation + '\n', encoding='utf-8')
    assert not failures(tree, 'adr_markers')
    output = checker['status_index'](tree)
    assert ('0001 | Fixture title | Accepted as an **INTERIM STANCE**. | '
            + implementation[:100] + '...\n') in output
    assert 'Body says Proposed' not in output


@pytest.mark.parametrize('field', ['Status', 'Implementation'])
def test_missing_adr_header_names_file(tree, field):
    value = 'Accepted' if field == 'Status' else 'Implemented'
    marker = f'{field}: {value}\n'
    edit(tree, 'decisions/0001-test.md', marker, '')
    findings = failures(tree, 'adr_markers')
    assert any(f['path'] == 'decisions/0001-test.md'
               and f'Expected at least one {field} marker' in f['message'] for f in findings)


@pytest.mark.parametrize('bold', [False, True])
@pytest.mark.parametrize('status,implementation', [
    ('Accepted', 'Implemented'),
    ('Proposed', 'None'),
    ('Superseded by ADR 0002', 'No separate handler'),
])
def test_repeated_body_headers_use_first_occurrence(tree, bold, status, implementation):
    status_prefix = '- **Status:** ' if bold else 'Status: '
    (tree / 'decisions/0001-test.md').write_text(
        '# Fixture title\n\n' + status_prefix + status + '\n'
        + 'Implementation: ' + implementation + '\n\n## Body\n'
        'Status: Proposed\nStatus: Accepted\nImplementation: Wrong body value\n',
        encoding='utf-8')
    assert not failures(tree, 'adr_markers')
    rows = [line for line in checker['status_index'](tree).splitlines()
            if line.startswith('0001 |')]
    assert rows == [f'0001 | Fixture title | {status} | {implementation}']


def test_status_groups_follow_only_status_prefix(tree):
    (tree / 'decisions/0008-test.md').write_text(
        '# Superseded title\n- **Status:** Superseded by ADR 0014. Accepted historically.\n'
        'Implementation: No separate handler\n', encoding='utf-8')
    edit(tree, 'decisions/0001-test.md', 'Status: Accepted',
         'Status: Accepted; superseded in part by ADR 0008')
    edit(tree, 'decisions/0027-test.md', '# 0027',
         '# Proposal title\n\nBody: Accepted and implemented.')
    output = checker['status_index'](tree)
    accepted, remaining = output.split('PROPOSED ADRS (DO NOT IMPLEMENT)\n')
    proposed, superseded = remaining.split('SUPERSEDED\n')
    superseded = superseded.split('OPEN GAPS\n')[0]
    assert '\n0001 |' in accepted and '\n0008 |' not in accepted and '\n0027 |' not in accepted
    assert '0027 | Proposal title | Proposed | None' in proposed
    assert '0008 | Superseded title | Superseded by ADR 0014. |' in superseded


def test_status_gaps_classified_only_by_subheading(tree):
    (tree / 'GAPS.md').write_text(
        '# Gaps\n## First section\n### Still open\nBody: resolved.\n'
        '### Partly resolved\nBody: unresolved work remains.\n'
        '## Resolved section name\n### Another open heading\n'
        '### RESOLVED issue\n### Unresolved literally contains resolved\n'
        '```text\n### resolved example\n```\n', encoding='utf-8')
    output = checker['status_index'](tree)
    opened, resolved = output.split('OPEN GAPS\n')[1].split(
        'RESOLVED OR PARTLY RESOLVED (headings only)\n')
    assert opened == ('First section\n  Still open\nResolved section name\n'
                      '  Another open heading\n\n')
    assert resolved == ('First section\n  Partly resolved\nResolved section name\n'
                        '  RESOLVED issue\n  Unresolved literally contains resolved\n')
    assert 'Body:' not in output and 'resolved example' not in output


def test_status_cli_exits_zero_without_running_checker(tree, monkeypatch, capsys):
    main = checker['main']
    original = checker['status_index']
    monkeypatch.setitem(main.__globals__, 'status_index', lambda: original(tree))
    def must_not_run():
        pytest.fail('status mode must not run the normal checker')
    monkeypatch.setitem(main.__globals__, 'check_repository', must_not_run)
    before = {p.relative_to(tree): p.read_bytes() for p in tree.rglob('*') if p.is_file()}
    assert main(['--status']) == 0
    assert capsys.readouterr().out == original(tree)
    assert before == {p.relative_to(tree): p.read_bytes() for p in tree.rglob('*') if p.is_file()}


def test_real_repository_status_matches_adr_files_and_identical_bytes():
    command = [sys.executable, '-B', str(ROOT / 'scripts/check_docs.py'), '--status']
    first = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
    second = subprocess.run(command, cwd=ROOT, capture_output=True, check=True,
                            env={**os.environ, 'PYTHONIOENCODING': 'cp1252'})
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == b''
    output = first.stdout.decode('utf-8')
    rows = [line for line in output.splitlines() if line[:4].isdigit() and ' | ' in line]
    paths = sorted((ROOT / 'decisions').glob('[0-9][0-9][0-9][0-9]-*.md'))
    assert len(rows) == len(paths)
    assert sorted(line[:4] for line in rows) == [path.name[:4] for path in paths]


def test_proposed_markers_and_reference_classification(tree):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\nProposed [ADR 0027](decisions/0027-test.md).')
    report = result(tree)
    assert report['checked']['proposed_references'] == 1
    assert not failures(tree, 'proposed_references')
    edit(tree, 'GAPS.md', 'Proposed [ADR', 'Accepted [ADR')
    assert failures(tree, 'proposed_references')
    edit(tree, 'GAPS.md', 'Accepted [ADR', 'See [ADR')
    assert any(f['check'] == 'proposed_references' for f in result(tree)['unchecked'])
    edit(tree, 'decisions/0027-test.md', 'Implementation: None', 'Implementation: Implemented')
    assert failures(tree, 'adr_markers')


@pytest.mark.parametrize('path,section', [
    ('design/nested/brief.md', 'design'),
    ('GAPS.md', 'baseline'),
    ('spec/design-notes.md', 'baseline'),
])
def test_reference_context_reported_in_its_source_section(tree, monkeypatch, capsys, path, section):
    before = result(tree)
    target = tree / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('# Context\n\nSee ADR 0027.\n', encoding='utf-8')
    report = result(tree)
    context = next(item for item in report['unchecked'] if item['path'] == path)
    assert context['check'] == 'proposed_references'
    assert len(report['unchecked']) == len(before['unchecked']) + 1
    for name in ('baseline', 'design'):
        assert report['unchecked_counts'][name] == before['unchecked_counts'][name] + (name == section)

    main = checker['main']
    monkeypatch.setitem(main.__globals__, 'check_repository', lambda: result(tree))
    assert main([]) == 0
    output = capsys.readouterr().out
    baseline, design = output.split('Design unchecked (in design/):')
    finding = f'UNCHECKED {path}:3 [proposed_references]'
    assert 'Baseline unchecked (outside design/):' in baseline
    assert finding in (design if section == 'design' else baseline)
    assert finding not in (baseline if section == 'design' else design)
    assert output.count(finding) == 1
    counts = report['unchecked_counts']
    assert (f"0 failures; {counts['baseline']} unchecked baseline; "
            f"{counts['design']} unchecked in design/ ({len(report['unchecked'])} total)") in output
    assert main(['--json']) == 0
    structured = json.loads(capsys.readouterr().out)
    assert structured['unchecked'] == report['unchecked']
    assert structured['unchecked_counts'] == counts


def test_design_acceptance_misrepresentation_remains_a_failure(tree, monkeypatch, capsys):
    (tree / 'design/brief.md').write_text(
        '# Draft\n\nADR 0027 is accepted.\nSee ADR 0027.\n', encoding='utf-8')
    report = result(tree)
    assert not report['ok']
    assert len(report['failures']) == 1
    assert report['failures'][0]['path'] == 'design/brief.md'
    assert report['failures'][0]['check'] == 'proposed_references'
    assert report['unchecked_counts']['design'] == 1
    main = checker['main']
    monkeypatch.setitem(main.__globals__, 'check_repository', lambda: result(tree))
    assert main([]) == 1
    output = capsys.readouterr().out
    failure = 'FAILURES design/brief.md:3 [proposed_references]'
    assert output.count(failure) == 1
    assert output.index(failure) < output.index('Baseline unchecked (outside design/):')
    assert '1 failures;' in output
    assert main(['--json']) == 1
    structured = json.loads(capsys.readouterr().out)
    assert structured['failures'] == report['failures']
    assert structured['unchecked_counts'] == report['unchecked_counts']


@pytest.mark.parametrize('claim', [
    'Accepted boundary: [0027](decisions/0027-test.md).',
    '[the identity decision](decisions/0027-test.md) is ratified.',
    '| [ADR 0027](decisions/0027-test.md) | Accepted |',
    '```text\nADR 0027 is accepted.\n```',
])
def test_explicit_acceptance_claims_for_proposals(tree, claim):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n' + claim)
    assert failures(tree, 'proposed_references')


@pytest.mark.parametrize('claim', [
    'ADR 0027 is not accepted.', 'Once ratified ADR 0027 may ship.',
    'If ADR 0027 is accepted, implementation may begin.',
    'Accepted ADR 0001 governs; ADR 0027 remains Proposed.',
])
def test_no_false_acceptance_clearance_for_negated_or_conditional_claims(tree, claim):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n' + claim)
    assert not failures(tree, 'proposed_references')


@pytest.mark.parametrize('numbers', [('2. **Second', '3. **Second'), ('2. **Second', '1. **Second')])
def test_invariant_gap_and_duplicate(tree, numbers):
    edit(tree, 'spec/NYX_ARCHITECTURE.md', *numbers)
    assert failures(tree, 'invariants')


@pytest.mark.parametrize('old,new', [
    ('"\\x1f"', '""'),
    ('prev_event_hash or ""', 'prev_event_hash or "zero"'),
    ('sorted(dependency_event_hashes)', 'dependency_event_hashes'),
    ('UTF8("" + event_hash)', 'UTF8("zero" + event_hash)'),
])
def test_hash_formula_changes(tree, old, new):
    edit(tree, 'spec/NYX_V0_IMPLEMENTATION.md', old, new)
    assert failures(tree, 'hash_formulas')


def test_hash_comparison_uses_shipped_helper_not_a_copied_formula(tree):
    edit(tree, 'src/nyx/hashing.py', '_SEP = "\\x1f"', '_SEP = "changed"')
    assert any('idempotency_key' in f['message'] for f in failures(tree, 'hash_formulas'))
    edit(tree, 'src/nyx/projection.py', '_GENESIS_VIEW_HASH = ""', '_GENESIS_VIEW_HASH = "changed"')
    assert any('genesis' in f['message'] for f in failures(tree, 'hash_formulas'))


def test_formula_prose_and_unsafe_expressions_are_not_evaluated(tree):
    edit(tree, 'spec/NYX_V0_IMPLEMENTATION.md', '# V0', '# V0\n'
         '`SHA256(prior || event_hash)`\n'
         '`SHA256(__import__("os").system("must-not-run"))`\n')
    report = result(tree)
    assert not [f for f in report['failures'] if f['check'] == 'hash_formulas']
    assert len([f for f in report['unchecked'] if 'Unchecked formula' in f['message'] and f['line'] in (2, 3)]) == 2


@pytest.mark.parametrize('old,new', [
    ('superseding_events          TEXT NOT NULL', 'different_column           TEXT NOT NULL'),
    ('current_value        TEXT,', 'current_value        INTEGER,'),
    ('current_value        TEXT,', 'current_value        TEXT CHECK (current_value != \'bad\'),'),
])
def test_legacy_schema_columns_and_constraints(tree, old, new):
    edit(tree, 'spec/NYX_V0_IMPLEMENTATION.md', old, new)
    assert failures(tree, 'legacy_schema')


def test_schema_does_not_execute_other_statements(tree):
    edit(tree, 'spec/NYX_V0_IMPLEMENTATION.md', '```sql\n',
         "```sql\nATTACH DATABASE 'do-not-create.sqlite' AS other;\n")
    assert failures(tree, 'legacy_schema') == []
    assert not (tree / 'do-not-create.sqlite').exists()


@pytest.mark.parametrize('block', ['```\ncode\n```\n', '```python\ncode\n'])
def test_fence_language_and_balance(tree, block):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n' + block)
    assert failures(tree, 'fences')


def test_tilde_and_longer_fences(tree):
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n~~~~text\n~~~\n~~~~\n'
         '````markdown\n```\n````\n')
    assert not failures(tree, 'fences')


@pytest.mark.parametrize('path', ['tests/test_example.py', 'src/nyx/hashing.py'])
def test_readme_map_missing_file(tree, path):
    edit(tree, 'README.md', path, 'tests/missing.py')
    assert failures(tree, 'readme_map')


def test_unlinked_map_file_is_checked(tree):
    edit(tree, 'README.md', '| [hash] |', '| `src/nyx/hashing.py` |')
    assert not failures(tree, 'readme_map')
    edit(tree, 'README.md', '`src/nyx/hashing.py`', '`src/nyx/missing.py`')
    assert failures(tree, 'readme_map')


@pytest.mark.parametrize('old,new', [
    ('ensure_ascii=False', 'ensure_ascii=True'),
    ('sort_keys=True', 'sort_keys=False'),
    ('sorted(encoded)', 'sorted(encoded, reverse=True)'),
])
def test_canonical_serialization_samples_detect_changed_helper(tree, old, new):
    edit(tree, 'src/nyx/hashing.py', old, new)
    assert failures(tree, 'serialization')


def test_cli_reports_all_failures_json_text_and_exit_code(tree, monkeypatch, capsys):
    main = checker['main']
    monkeypatch.setitem(main.__globals__, 'check_repository', lambda: result(tree))
    assert main(['--fix-none', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['ok']
    edit(tree, 'GAPS.md', '# Gaps', '# Gaps\n[a](one.md)\n[b](two.md)\n')
    assert main(['--json']) == 1
    data = json.loads(capsys.readouterr().out)
    assert len(data['failures']) == 2
    assert main([]) == 1
    output = capsys.readouterr().out
    assert 'one.md' in output and 'two.md' in output and 'UNCHECKED' in output
    with pytest.raises(SystemExit) as refused:
        main(['--fix'])
    assert refused.value.code == 2
