#!/usr/bin/env python3
"""Deterministic valid-store campaign; no undecided stage-two event semantics.

Legacy corrections are never backdated (ADR 0005). Stage two contains only
constitutive mentions and observations (ADR 0023). Complete live publications
are compared with genesis replay at a shared time, including every field.
Projector 3 additionally exercises ordinary corrections, replacement and expiry.
ADR 0012 permits evaluation-time relabeling for this time-independent reducer
only after establishing publication at the same log tip. No historical view is
obtained by relabeling current rows.
"""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import sys
import tempfile
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nyx import events, hashing, ingestion, projection, storage, writer
from verify_store import verify_store

BASE = datetime(2026, 7, 13, tzinfo=timezone.utc)
AS_OF = (BASE + timedelta(days=10)).isoformat()
VALUES = ('', 'é', 'e\u0301', '東京🦉', 'x' * 4096, '0', 'line\n\x00end', 'ß')
LABELS = ('externally_checkable', 'locally_checkable', 'subjective', 'structurally_unverifiable')


def stamp(at, rng):
    offset = rng.choice((-720, -330, 0, 345, 840))
    text = at.astimezone(timezone(timedelta(minutes=offset))).isoformat(
        timespec=rng.choice(('seconds', 'milliseconds', 'microseconds')))
    return text.replace('+00:00', 'Z') if offset == 0 and rng.randrange(2) else text


def generate(projector_version, seed, count):
    if projector_version == '3':
        return generate_forward(seed, count)
    if projector_version not in ('0', '1', '2') or count < 6:
        raise ValueError('select projector 0/1/2 and at least six events')
    rng = random.Random(seed)
    result, latest = [], {}
    for i in range(count):
        source = {'actor_id': f'actor-{i % 4}', 'config': {'seed': seed, 'text': VALUES[i % 4]}}
        # Recording times are monotonic by instant, with equal adjacent times.
        recorded = stamp(BASE + timedelta(days=5, seconds=i // 2), rng)
        at = BASE + timedelta(seconds=rng.randrange(4000), microseconds=rng.choice((0, 123000, 123456)))
        event_type = events.OBSERVATION_RECORDED
        if projector_version == '0':
            bid = f'b-{rng.randrange(6)}'
            if i % 5 == 4:
                event_type = events.CORRECTION_APPENDED
                at = max(at, latest.get(bid, BASE)) + timedelta(seconds=1)
            occurred = stamp(at, rng)
            instant = datetime.fromisoformat(occurred)
            latest[bid] = max(instant, latest.get(bid, instant))
            data = {'belief_id': bid, 'value': VALUES[i % len(VALUES)],
                    'verifiability': LABELS[i % len(LABELS)]}
        elif i < 3:
            event_type = events.ENTITY_MENTION_RECORDED
            occurred = stamp(at, rng)
            data = {'mention_id': f'm-{i}', 'subject_id': f's-{i}',
                    'text': VALUES[i + 1], 'link_state': 'constitutive'}
        else:
            occurred = stamp(at, rng)
            pairs = rng.sample([(s, p) for s in range(3) for p in range(3)], rng.choice((1, 2, 3)))
            data = {'claims': [dict(mention_id=f'm-{s}', subject_id=f's-{s}',
                property_id=f'prop-{p}', belief_id=f'b-{s}-{p}',
                claim_candidate_id=f'c-{i}-{j}', value=VALUES[(i - 3 + j) % len(VALUES)],
                verifiability=LABELS[(i + j) % len(LABELS)])
                for j, (s, p) in enumerate(pairs)]}
        result.append(dict(event_id=f'event-{seed}-{i}', event_type=event_type,
                           occurred_at=occurred, recorded_at=recorded, source=source, data=data))
    return result


def generate_forward(seed, count):
    """Retain the frozen generator; add explicit live-target transitions for 3."""
    steps = generate('2', seed, count)
    rng, live = random.Random(seed + 3000), {}
    for index, step in enumerate(steps):
        if step['event_type'] == events.ENTITY_MENTION_RECORDED:
            continue
        if live and index % 4 != 3:
            cid = rng.choice(sorted(live))
            target, stamp_value = live.pop(cid)
            kind = (events.CORRECTION_APPENDED, events.CANDIDATE_REPLACED, events.CANDIDATE_EXPIRED)[index % 4]
            step['event_type'] = kind
            if kind == events.CANDIDATE_EXPIRED:
                data = {'belief_id': target['belief_id'], 'targets': [cid]}
            else:
                claim = {**target, 'claim_candidate_id': f'transition-{index}', 'value': VALUES[index % len(VALUES)]}
                data = {'claim': claim, 'targets': [cid]}
                if kind == events.CORRECTION_APPENDED:
                    step['occurred_at'] = stamp(max(datetime.fromisoformat(step['occurred_at']),
                        datetime.fromisoformat(stamp_value)) + timedelta(seconds=1), rng)
                live[claim['claim_candidate_id']] = (claim, step['occurred_at'])
            data['basis'] = {'kind': 'stated_error' if kind == events.CORRECTION_APPENDED else 'stated',
                             'statement': f'generated transition {index}'}
            step['data'] = data
        else:
            for claim in step['data']['claims']:
                live[claim['claim_candidate_id']] = (claim, step['occurred_at'])
    return steps


def prepare(conn, step, projector_version):
    common = dict(source=step['source'], source_class='direct_observation',
                  occurred_at=step['occurred_at'], event_id=step['event_id'])
    if projector_version == '0':
        return writer.prepare_event(**common, event_type=step['event_type'],
                                    origin_type='observed', payload=step['data'])
    if step['event_type'] == events.ENTITY_MENTION_RECORDED:
        data = step['data']
        return ingestion.prepare_mention(conn, **common, origin_type='observed',
            mention_id=data['mention_id'], subject_id=data['subject_id'], text=data['text'])
    if projector_version == '3' and step['event_type'] != events.OBSERVATION_RECORDED:
        data = step['data']
        bid = data['belief_id'] if step['event_type'] == events.CANDIDATE_EXPIRED else data['claim']['belief_id']
        subject = storage.read_snapshot(conn, projector_version).header(bid)['subject_id']
        return writer.prepare_event(**common, event_type=step['event_type'], origin_type='observed',
                                    payload=data, entity_refs=[subject])
    return ingestion.prepare_observation(conn, **common, claims=step['data']['claims'],
                                         projector_version=projector_version)


def publication(conn, projector_version, as_of=AS_OF):
    if projector_version == '0':
        keys = [row[0] for row in conn.execute('SELECT belief_id FROM resolved_beliefs')]
        complete = {'beliefs': {key: storage.read_belief(conn, key, '0') for key in keys}}
    else:
        complete = storage.read_snapshot(conn, projector_version).complete()
    # The caller proves the progress/tip equality before this normalization.
    for belief in complete['beliefs'].values():
        belief['projected_as_of'] = as_of
    return complete


def assert_equivalent(conn, projector_version, as_of=AS_OF):
    tip = conn.execute('SELECT rowid,event_id FROM events ORDER BY rowid DESC LIMIT 1').fetchone()
    progress = conn.execute('SELECT log_position,event_id FROM derived_progress WHERE projector_version=?',
                            (projector_version,)).fetchone()
    assert progress == tip, (projector_version, progress, tip)
    log = storage.read_all_events(conn)
    expected = ({'beliefs': projection.project(log, as_of, '0')} if projector_version == '0' else
                projection.project_snapshot(log, as_of, projector_version).complete())
    actual = publication(conn, projector_version, as_of)
    assert hashing.canonical_json(actual) == hashing.canonical_json(expected), (projector_version, len(log))
    assert storage.evaluate_whole_view(conn, as_of, projector_version) == expected['beliefs']
    if projector_version == '3':
        snapshot = projection.project_snapshot(log, as_of, projector_version)
        for bid in expected['beliefs']:
            assert storage.read_candidate_sets(conn, bid, projector_version) == snapshot.candidate_sets(bid)


def build(path, projector_version, seed, count, *, check_prefixes=False):
    steps = generate(projector_version, seed, count)
    requests = []
    with closing(storage.init_db(path, create=True, clock=lambda: BASE.isoformat(), threshold=timedelta(seconds=120))) as conn:
        for i, step in enumerate(steps):
            conn.clock = lambda s=step: s['recorded_at']
            request = prepare(conn, step, projector_version)
            requests.append(request)
            ingestion.submit(conn, request, (BASE + timedelta(days=6, seconds=i)).isoformat(), projector_version)
            if check_prefixes:
                assert_equivalent(conn, projector_version)
        assert_equivalent(conn, projector_version)
    return requests


def exercise(path, projector_version, seed, count, *, check_prefixes=False):
    requests = build(path, projector_version, seed, count, check_prefixes=check_prefixes)
    report = verify_store(path, projector_version)
    assert report['ok'] and report['freshness']['state'] == 'current' and not report['pending'], report
    with closing(storage.init_db(path, clock=lambda: (BASE + timedelta(days=7)).isoformat(),
                                 threshold=timedelta(seconds=120))) as conn:
        before = storage.read_all_events(conn)
        order = list(requests)
        random.Random(seed + 1).shuffle(order)
        for request in order:
            committed = ingestion.submit(conn, request, AS_OF, projector_version)
            assert committed[0].event_id == request[0].event_id
        assert storage.read_all_events(conn) == before
        assert_equivalent(conn, projector_version)
    report = verify_store(path, projector_version)
    assert report['ok'] and not report['pending'], report
    return dict(projector=projector_version, seed=seed, events=count, retries=len(requests))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=100)
    parser.add_argument('--events', type=int, default=80)
    parser.add_argument('--minutes', type=float, default=45)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    started, results = monotonic(), []
    with tempfile.TemporaryDirectory(prefix='nyx-replay-') as temp:
        for seed in range(args.seeds):
            for projector_version in ('0', '1', '2', '3'):
                if monotonic() - started >= args.minutes * 60:
                    break
                path = Path(temp) / f'{projector_version}-{seed}.db'
                results.append(exercise(path, projector_version, seed, args.events))
                if args.output:
                    args.output.write_text(json.dumps(dict(results=results), indent=2) + '\n', encoding='utf-8')
            else:
                print(f'Completed seed {seed}: {len(results)} sequences', flush=True)
                continue
            break
    summary = dict(sequences=len(results), events=sum(r['events'] for r in results),
                   retries=sum(r['retries'] for r in results),
                   seeds=sorted({r['seed'] for r in results}), seconds=round(monotonic() - started, 3),
                   results=results)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'results'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
