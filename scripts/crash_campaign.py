#!/usr/bin/env python3
"""Kill real SQLite writers at documented transaction/recovery boundaries.

Instrumentation is subprocess-local SQL tracing, never a production failpoint.
Each child announces its actual PID and blocks with an open transaction where
appropriate. The parent proves committed-reader isolation, kills that process,
then uses materialize_pending / rebuild_projection and retained request retries.
"""
import argparse
from collections import Counter
from contextlib import closing
from dataclasses import asdict
from datetime import timedelta
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
import tempfile
from threading import Thread
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_campaign import AS_OF, assert_equivalent, build, generate, prepare, publication
from nyx import ingestion, storage, writer
from verify_store import verify_store

POINTS = ('before_append_commit', 'after_append', 'mid_publication', 'mid_rebuild', 'after_publication')


def pause(conn, point):
    print(json.dumps(dict(pid=os.getpid(), point=point, transaction=conn.in_transaction)), flush=True)
    sys.stdin.read()  # Parent owns stdin until process death.
    raise RuntimeError('crash child unexpectedly resumed')


def child(path, projector_version, point, manifest):
    saved = json.loads(Path(manifest).read_text(encoding='utf-8'))
    request = writer.EventRequest(**saved['envelope']), writer.PayloadRequest(**saved['payload'])
    with closing(storage.init_db(path, clock=lambda: saved['clock'], threshold=timedelta(seconds=120))) as conn:
        if point == 'before_append_commit':
            def trace(sql):
                if sql.upper().startswith('INSERT INTO PAYLOADS'):
                    pause(conn, point)  # Event row inserted; append transaction not committed.
            conn.set_trace_callback(trace)
            storage.append_submission(conn, request, projector_version)
        else:
            storage.append_submission(conn, request, projector_version)
            if point == 'after_append':
                pause(conn, point)
            elif point == 'mid_publication':
                boundary = {'0': 'INSERT INTO DERIVED_PROGRESS', '1': 'INSERT INTO PROJECTED_EVENTS',
                            '2': 'INSERT INTO COMMITTED_ROOTS'}[projector_version]
                conn.set_trace_callback(lambda sql: pause(conn, point)
                                        if sql.upper().startswith(boundary) else None)
                storage.materialize_pending(conn, AS_OF, projector_version)
            else:
                storage.materialize_pending(conn, AS_OF, projector_version)
                if point == 'after_publication':
                    pause(conn, point)
                elif point == 'mid_rebuild':
                    # All clearing and the first replay delta are inside this
                    # transaction; pause before its first progress write.
                    conn.set_trace_callback(lambda sql: pause(conn, point)
                                            if sql.upper().startswith('INSERT INTO DERIVED_PROGRESS') else None)
                    storage.rebuild_projection(conn, AS_OF, projector_version)
                else:
                    raise ValueError(point)
    raise RuntimeError(f'kill point was not reached: {point}')


def exercise(directory, projector_version, seed, point):
    if projector_version == '0' and point == 'mid_rebuild':
        raise NotImplementedError('rebuild_projection requires the snapshot boundary (projectors 1/2)')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'nyx.db'
    requests = build(path, projector_version, seed, 6)
    step = generate(projector_version, seed, 7)[6]
    with closing(storage.init_db(path, clock=lambda: step['recorded_at'], threshold=timedelta(seconds=120))) as conn:
        request = prepare(conn, step, projector_version)
        before = storage.read_all_events(conn)
        old_publication = publication(conn, projector_version)
    manifest = directory / 'nyx.db.imports' / 'request.json'
    manifest.parent.mkdir()
    manifest.write_text(json.dumps(dict(envelope=asdict(request[0]), payload=asdict(request[1]),
                                       clock=step['recorded_at']), ensure_ascii=False), encoding='utf-8')
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                   'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
    # Windows venv redirectors can leave a child alive if killed. Launch the
    # real executable and verify the process announcing the pause is its owner.
    proc = subprocess.Popen([sys._base_executable, '-B', str(Path(__file__).resolve()),
                             '--child', str(path), projector_version, point, str(manifest)],
                            env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    ready = Queue()
    thread = Thread(target=lambda: ready.put(proc.stdout.readline()), daemon=True)
    thread.start()
    expected_count = 6 if point == 'before_append_commit' else 7
    try:
        line = ready.get(timeout=15)
        assert line, f'child exited before pause: {proc.communicate(timeout=15)}'
        message = json.loads(line)
        assert message['pid'] == proc.pid and message['point'] == point, message
        assert message['transaction'] == (point in ('before_append_commit', 'mid_publication', 'mid_rebuild'))
        with closing(storage.open_readonly(path)) as reader:
            visible = storage.read_all_events(reader)
            assert len(visible) == expected_count
            assert visible[:6] == before  # Every previously committed byte survives.
            if point in ('before_append_commit', 'after_append', 'mid_publication'):
                assert publication(reader, projector_version) == old_publication
            else:
                assert_equivalent(reader, projector_version)
        report = verify_store(path, projector_version)
        assert report['ok'], report
        assert len(report['pending']) == (1 if point in ('after_append', 'mid_publication') else 0), report
        proc.kill()
        proc.wait(timeout=15)
        assert proc.returncode != 0
    finally:
        if proc.poll() is None:
            proc.kill()
        stdout, stderr = proc.communicate(timeout=15)
        thread.join(timeout=1)
    assert not stderr, stderr
    with closing(storage.init_db(path, clock=lambda: step['recorded_at'], threshold=timedelta(seconds=120))) as conn:
        committed_before_recovery = storage.read_all_events(conn)
        assert len(committed_before_recovery) == expected_count
        # Exercise supported recovery paths on every restart; neither may append.
        storage.materialize_pending(conn, AS_OF, projector_version)
        assert_equivalent(conn, projector_version)
        if projector_version in ('1', '2'):
            storage.rebuild_projection(conn, AS_OF, projector_version)
        assert storage.read_all_events(conn) == committed_before_recovery
        assert_equivalent(conn, projector_version)
        result = ingestion.submit(conn, request, AS_OF, projector_version)
        assert result[0].event_id == request[0].event_id
        all_requests = [*requests, request]
        retained = storage.read_all_events(conn)
        assert len(retained) == 7
        for retry in [*all_requests, request]:
            ingestion.submit(conn, retry, AS_OF, projector_version)
        assert storage.read_all_events(conn) == retained
        assert_equivalent(conn, projector_version)
    report = verify_store(path, projector_version)
    assert report['ok'] and not report['pending'] and report['freshness']['state'] == 'current', report
    return dict(projector=projector_version, seed=seed, point=point, committed_at_kill=expected_count,
                events_after_retry=7, retries=8)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', nargs=4, metavar=('DB', 'VERSION', 'POINT', 'MANIFEST'))
    parser.add_argument('--seeds', type=int, default=20)
    parser.add_argument('--minutes', type=float, default=30)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.child:
        child(*args.child)
        return
    started, results = monotonic(), []
    with tempfile.TemporaryDirectory(prefix='nyx-crashes-') as temp:
        for seed in range(args.seeds):
            for projector_version in ('0', '1', '2'):
                for point in POINTS:
                    if projector_version == '0' and point == 'mid_rebuild':
                        continue  # Existing documented API supports snapshot versions 1/2 only.
                    if monotonic() - started >= args.minutes * 60:
                        raise TimeoutError('crash campaign budget exhausted')
                    results.append(exercise(Path(temp) / f'{seed}-{projector_version}-{point}', projector_version, seed, point))
            print(f'Seed {seed}: {len(results)} killed writers recovered', flush=True)
    summary = dict(kills=len(results), events=sum(r['events_after_retry'] for r in results),
                   retries=sum(r['retries'] for r in results), seeds=list(range(args.seeds)),
                   points=dict(Counter(r['point'] for r in results)),
                   skipped=['projector 0 mid_rebuild: storage._snapshot_projector refuses version 0'],
                   seconds=round(monotonic() - started, 3), results=results)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}))


if __name__ == '__main__':
    main()
