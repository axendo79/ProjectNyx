#!/usr/bin/env python3
"""Disposable-store mutation matrix, including self-consistent commitments.

Copies use SQLite's backup API. Constraints/triggers are removed ONLY from
the mutated copy when simulating physical corruption that SQL normally blocks.
No production store or hook is bypassed. Controls that swap identical values
are labeled CONTROL, never counted as verifier successes or escapes.
"""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_campaign import build, publication
from nyx import hashing, storage
from verify_store import FIELDS, verify_store


def backup(source, target):
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)


def relax(conn, table):
    # Column names/types/row order survive; uniqueness and CHECKs do not.
    conn.execute(f'CREATE TABLE mutant_copy AS SELECT * FROM {table} ORDER BY rowid')
    conn.execute(f'DROP TABLE {table}')
    conn.execute(f'ALTER TABLE mutant_copy RENAME TO {table}')


def flip(value):
    if value is None:
        return 'x'
    if isinstance(value, int):
        return value ^ 1
    if isinstance(value, float):
        return value + 0.25
    return chr(ord(value[0]) ^ 1) + value[1:] if value else 'x'


def field_mutation(conn, table, field, operation):
    relax(conn, table)
    rows = conn.execute(f'SELECT rowid,{field} FROM {table} ORDER BY rowid').fetchall()
    if not rows:
        return False
    rowid, value = next(((r, v) for r, v in rows if v is not None), rows[0])
    if operation == 'flip':
        conn.execute(f'UPDATE {table} SET {field}=? WHERE rowid=?', (flip(value), rowid))
    elif operation == 'delete':
        conn.execute(f'DELETE FROM {table} WHERE rowid=?', (rowid,))
    elif operation == 'duplicate':
        conn.execute(f'INSERT INTO {table} SELECT * FROM {table} WHERE rowid=?', (rowid,))
    elif operation == 'swap':
        before = sorted(hashing.canonical_json(list(row)) for row in conn.execute(f'SELECT * FROM {table}'))
        other = next(((r, v) for r, v in rows if v != value), None)
        if other is None:
            return False
        conn.execute(f'UPDATE {table} SET {field}=? WHERE rowid=?', (other[1], rowid))
        conn.execute(f'UPDATE {table} SET {field}=? WHERE rowid=?', (value, other[0]))
        # Swapping index keys with identical associated data can merely exchange
        # physical rows. That preserves the logical multiset and is a control.
        after = sorted(hashing.canonical_json(list(row)) for row in conn.execute(f'SELECT * FROM {table}'))
        return after != before
    else:
        raise ValueError(operation)
    return True


def rehash_legacy(conn, field):
    relax(conn, 'events')
    rows = [dict(zip(FIELDS, row)) for row in conn.execute(f"SELECT {','.join(FIELDS)} FROM events ORDER BY rowid")]
    rows[0][field] = '0' * 64 if field == 'idempotency_key' else '999'
    prior, views = None, {}
    for row in rows:
        row['prev_event_hash'] = prior
        material = {k: v for k, v in row.items() if k not in ('event_hash', 'prev_event_hash')}
        row['event_hash'] = hashing.event_hash(material, prior)
        conn.execute('UPDATE events SET prev_event_hash=?,event_hash=?,idempotency_key=?,schema_version=? WHERE event_id=?',
                     (prior, row['event_hash'], row['idempotency_key'], row['schema_version'], row['event_id']))
        data = json.loads(conn.execute('SELECT ciphertext FROM payloads WHERE event_id=?', (row['event_id'],)).fetchone()[0])
        bid = data['belief_id']
        views[bid] = hashing._sha256_hex(views.get(bid, '') + row['event_hash'])
        conn.execute('UPDATE entity_event_index SET latest_event_hash=? WHERE latest_event_id=?',
                     (row['event_hash'], row['event_id']))
        prior = row['event_hash']
    for bid, digest in views.items():
        conn.execute('UPDATE resolved_beliefs SET view_version_hash=? WHERE belief_id=?', (digest, bid))


def mutate(path, version, case):
    with closing(sqlite3.connect(path)) as conn, conn:
        if case.startswith('legacy/'):
            rehash_legacy(conn, case.split('/')[1])
            return True
        if case == 'nodes/branch/rehash':
            row = conn.execute("SELECT content FROM committed_nodes WHERE json_extract(content,'$.kind')='branch' LIMIT 1").fetchone()
            bad = json.loads(row[0])
            bad['left'], bad['right'] = bad['right'], bad['left']
            raw = hashing.canonical_json(bad)
            conn.execute("INSERT INTO committed_nodes VALUES ('2',?,?)", (hashing._sha256_hex(raw), raw))
            return True
        if case == 'publication/delete':
            table = 'resolved_beliefs' if version == '0' else 'projected_beliefs'
            return field_mutation(conn, table, 'belief_id', 'delete')
        if case.startswith('freshness/'):
            table = 'entity_event_index' if version == '0' else 'identity_event_index'
            return field_mutation(conn, table, 'latest_event_id', case.split('/')[1])
        table, field, operation = case.split('/')
        if table == 'nodes':
            table = 'committed_nodes'
            field = 'node_hash' if field == 'hash' else field
        return field_mutation(conn, table, field, operation)


def classify(path, version, case):
    report = verify_store(path, version)
    production = []
    # Reads only: no recovery silently replaces the mutant being inspected.
    operations = {'log': lambda conn: storage.read_all_events(conn),
                  'publication': lambda conn: publication(conn, version),
                  'status': lambda conn: storage.read_projection_status(conn, version)}
    for name, operation in operations.items():
        try:
            with closing(storage.open_readonly(path)) as conn:
                operation(conn)
        except (ValueError, RuntimeError, NotImplementedError, sqlite3.Error, KeyError, TypeError) as error:
            production.append(f'{name}: {type(error).__name__}: {error}')
    return dict(projector=version, case=case,
                outcome='CAUGHT' if not report['ok'] else 'PRODUCTION ONLY' if production else 'ESCAPED',
                checks=sorted({f['check'] for f in report['failures']}),
                failures=report['failures'], production=production, unchecked=report['unchecked'])


def cases(path, version):
    tables = ['events', 'payloads', 'derived_progress']
    tables += (['resolved_beliefs', 'entity_event_index'] if version == '0' else
               ['projected_beliefs', 'identity_event_index', 'belief_event_index'])
    tables += (['projected_entities', 'projected_mentions', 'projected_entity_links',
                'projected_claim_candidates', 'projected_events'] if version == '1' else
               ['committed_nodes', 'committed_roots'] if version == '2' else [])
    result = []
    with closing(sqlite3.connect(path)) as conn:
        for table in tables:
            fields = [row[1] for row in conn.execute(f'PRAGMA table_info({table})')]
            for field in fields:
                result.extend(f'{table}/{field}/{op}' for op in ('flip', 'swap'))
            result.extend(f'{table}/{fields[0]}/{op}' for op in ('delete', 'duplicate'))
    result += ['publication/delete', 'freshness/delete', 'freshness/swap']
    if version == '0':
        result += ['legacy/idempotency_key/rehash', 'legacy/schema_version/rehash']
    if version == '2':
        result += ['nodes/branch/rehash']
    return result


def campaign(directory, seed=17, count=12, minutes=45):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    results, started = [], monotonic()
    for version in ('0', '1', '2'):
        base = directory / f'base-{version}.db'
        build(base, version, seed, count)
        assert verify_store(base, version)['ok']
        for index, case in enumerate(cases(base, version)):
            if monotonic() - started >= minutes * 60:
                raise TimeoutError('mutation campaign budget exhausted before matrix completion')
            target = directory / f'mutant-{version}-{index}.db'
            backup(base, target)
            changed = mutate(target, version, case)
            result = classify(target, version, case) if changed else dict(
                projector=version, case=case, outcome='CONTROL', checks=[], production=[])
            results.append(result)
        print(f'Projector {version}: {len(results)} cumulative cases', flush=True)
    return results


def write_matrix(path, results):
    counts = Counter(r['outcome'] for r in results)
    lines = ['# Queue 6 verifier mutation matrix', '',
             'Disposable SQLite-backup copies of generator stores (seed 17, 12 events/projector).',
             'SQL constraints/triggers removed only in mutant copies; unchanged swaps are controls.',
             '', f'Totals: {dict(counts)}', '',
             '| Projector | Mutation | Outcome | Named checks / production refusal |',
             '| --- | --- | --- | --- |']
    for result in results:
        detail = ('unchanged logical row multiset' if result['outcome'] == 'CONTROL' else
                  ', '.join(result['checks']) or '; '.join(result['production']) or 'See findings below')
        lines.append(f"| {result['projector']} | {result['case']} | {result['outcome']} | {detail.replace('|', '/')} |")
    lines += ['', '## Escapes and production-only findings', '']
    for result in results:
        if result['outcome'] in ('ESCAPED', 'PRODUCTION ONLY'):
            lines += [f"### {result['projector']} — {result['case']}", '',
                      'Reproduction: build a fresh generator store, then call `mutate(path, version, case)`.',
                      f"Verifier outcome: {result['outcome']}; production refusals: {result['production']!r}.",
                      f"Explicit unchecked checks: {result.get('unchecked', [])!r}.", '']
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='nyx-mutations-') as temp:
        results = campaign(temp)
    write_matrix(args.output, results)
    args.json.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(dict(Counter(r['outcome'] for r in results)))


if __name__ == '__main__':
    main()
