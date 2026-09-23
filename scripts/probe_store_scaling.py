"""Standalone whole-store probe; run explicitly, not as a CI benchmark.

Each fresh store has one mention and five single-claim observations per subject,
all on that subject's one property, with fixed 200-byte ASCII values. Event scales
round to the nearest complete six-event subject (at least one). IDs, timestamps
and source metadata are fixture inputs, not production ingestion defaults.

Ingestion includes preparation, submit, append and publication, excluding database
creation. Verification times the independent verify_store operation, including its
read-only connection, but excluding process startup. Node content bytes are the
UTF-8 bytes in committed_nodes.content, including retained historical nodes; they
exclude Layer A, headers, SQL/index overhead and write amplification. Projector 1
has no committed nodes, so those metrics are zero. File bytes are the main SQLite
file after a successful truncating WAL checkpoint and connection closure, including
all tables, indexes and free pages. They are not cumulative bytes written.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import platform
import sys
import tempfile
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from nyx import ingestion, storage
from verify_store import verify_store


START = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = {'actor_id': 'store-probe', 'config': {}}
VALUE = 'x' * 200


def sample(requested_events, projector_version):
    """Measure one fresh database using the existing production writer path."""
    if requested_events < 1 or projector_version not in ('1', '2'):
        raise ValueError('positive event count and projector 1 or 2 required')
    subjects = max(1, (requested_events + 3) // 6)
    event_count = subjects * 6
    with tempfile.TemporaryDirectory(prefix='nyx-store-probe-') as directory:
        path = Path(directory) / 'store.sqlite'
        at = START.isoformat()
        with closing(storage.init_db(path, create=True, clock=lambda: at,
                                     threshold=timedelta(seconds=120))) as conn:
            started = perf_counter()
            for subject in range(subjects):
                sid, mid, bid = (f'{prefix}-{subject:06d}' for prefix in ('s', 'm', 'b'))
                for offset in range(6):
                    position = subject * 6 + offset
                    at = (START + timedelta(seconds=position)).isoformat()
                    common = dict(source=SOURCE, source_class='direct_observation',
                                  occurred_at=at, event_id=f'e-{position:06d}')
                    if offset == 0:
                        pair = ingestion.prepare_mention(
                            conn, mention_id=mid, subject_id=sid, text=f'fixture {subject:06d}',
                            origin_type='observed', **common)
                    else:
                        pair = ingestion.prepare_observation(conn, claims=[dict(
                            mention_id=mid, subject_id=sid, belief_id=bid,
                            property_id='fixture.value', claim_candidate_id=f'c-{position:06d}',
                            value=VALUE, verifiability='externally_checkable')],
                            projector_version=projector_version, **common)
                    if not ingestion.submit(conn, pair, at, projector_version):
                        raise RuntimeError('fixture unexpectedly retried an event')
            ingestion_seconds = perf_counter() - started
            actual = conn.execute('SELECT count(*) FROM events').fetchone()[0]
            nodes, node_bytes = conn.execute(
                'SELECT count(*), coalesce(sum(length(CAST(content AS BLOB))),0) '
                'FROM committed_nodes WHERE projector_version=?', (projector_version,)).fetchone()
            checkpoint = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if actual != event_count or checkpoint != (0, 0, 0):
                raise RuntimeError('incorrect event count or incomplete WAL checkpoint')
        file_bytes = path.stat().st_size
        started = perf_counter()
        verified = verify_store(path, projector_version)
        verifier_seconds = perf_counter() - started
        if (not verified['ok'] or verified['event_count'] != event_count
                or verified['freshness']['state'] != 'current'):
            raise RuntimeError(f'probe verification failed: {verified}')
        return dict(projector_version=projector_version, requested_events=requested_events,
                    events=event_count, subjects=subjects, ingestion_seconds=ingestion_seconds,
                    verifier_seconds=verifier_seconds, committed_nodes=nodes,
                    node_content_bytes=node_bytes, content_bytes_per_event=node_bytes / event_count,
                    file_bytes=file_bytes, file_bytes_per_event=file_bytes / event_count,
                    verified=True)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be positive')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=positive_int, default=[300, 600, 1200, 2400])
    parser.add_argument('--skip-projector-1', action='store_true')
    parser.add_argument('--projector-1-max-events', type=positive_int,
                        help='skip projector-1 samples whose rounded event count exceeds this cap')
    parser.add_argument('--json', type=Path, help='save measurements and metric definitions')
    args = parser.parse_args(argv)
    report = dict(python=platform.python_version(), platform=platform.platform(),
                  workload='one mention + five observations per subject; one property; 200-byte values',
                  content_bytes='UTF-8 committed_nodes.content only; retained nodes included; zero for 1',
                  file_bytes='main SQLite file after TRUNCATE checkpoint and writer close',
                  samples=[], skipped=[])
    print(f"Python {report['python']} | {report['platform']}", flush=True)
    print('Content = retained node UTF-8 bytes; file = checkpointed database bytes.', flush=True)
    print('projector events ingest_s verify_s nodes content_bytes content_B/event file_bytes file_B/event', flush=True)
    for version in ('1', '2'):
        for requested in args.sizes:
            count = max(1, (requested + 3) // 6) * 6
            if version == '1' and (args.skip_projector_1 or (
                    args.projector_1_max_events is not None and count > args.projector_1_max_events)):
                report['skipped'].append(dict(projector_version=version, requested_events=requested,
                                              events=count, reason='explicit projector-1 skip/cap'))
                print(f'{version} {count} SKIPPED (explicit projector-1 skip/cap)', flush=True)
                continue
            row = sample(requested, version)
            report['samples'].append(row)
            print(f"{version} {row['events']} {row['ingestion_seconds']:.6f} "
                  f"{row['verifier_seconds']:.6f} {row['committed_nodes']} "
                  f"{row['node_content_bytes']} {row['content_bytes_per_event']:.2f} "
                  f"{row['file_bytes']} {row['file_bytes_per_event']:.2f}", flush=True)
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
