"""Reproducible bounded investigation; all writes are disposable fixture/evidence files."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import cProfile
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from nyx import events, forward, hashing, ingestion, merkle, storage
from deephist_prototype import IndexedSnapshot, indexed_dependencies, verifier

OUT = ROOT / "design" / "deephist-evidence"
LOCAL = ROOT / "scratch" / "deephist"
START = datetime(2026, 7, 13, tzinfo=timezone.utc)
AS_OF = (START + timedelta(days=2)).isoformat()
LIMIT = 1200
SIZES = [250, 500, 1000, 2000]


def save(name, data):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def fixture(shape, count, version):
    previous = None
    for i in range(count):
        group = (i - 1) // 5 if shape == "spread" and i > 0 else 0
        mid, sid, bid = "m-000000", "s-000000", f"b-{group:06d}"
        stamp = (START + timedelta(seconds=i)).isoformat()
        if i == 0:
            kind = events.ENTITY_MENTION_RECORDED
            data = dict(mention_id=mid, subject_id=sid, text=f"fixture {group}", link_state="constitutive")
        else:
            claim = dict(mention_id=mid, subject_id=sid, belief_id=bid,
                         property_id=f"fixture.value.{group}" if shape == "spread" else "fixture.value",
                         claim_candidate_id=f"c-{i:06d}",
                         value="x" * 200, verifiability="externally_checkable")
            if shape == "transitions" and i >= 2:
                kind = events.CANDIDATE_REPLACED
                data = dict(claim=claim, targets=[f"c-{i-1:06d}"],
                            basis=dict(kind="stated", statement="deterministic replacement"))
            else:
                kind = events.OBSERVATION_RECORDED
                data = dict(claims=[claim])
        pair = events.build_event(event_id=f"e-{i:06d}", event_type=kind,
            origin_type="observed", source=dict(actor_id="deephist-synthetic", config={}),
            source_class="direct_observation", occurred_at=stamp, recorded_at=stamp,
            payload=data, prev_event_hash=previous, entity_refs=[sid])
        previous = pair[0].event_hash
        yield pair[0], pair[1], data


def dbpath(shape, count, version):
    LOCAL.mkdir(parents=True, exist_ok=True)
    return LOCAL / f"{shape}-{version}-{count}.sqlite"


def profile_text(profile):
    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative")
    stats.print_stats(35)
    stats.print_callers("rebuild")
    return stream.getvalue()


def build(shape, count, version):
    path = dbpath(shape, count, version)
    if path.exists():
        raise RuntimeError(f"fixture already exists: {path}")
    times = []
    progress = []
    with closing(storage.init_db(path, create=True)) as conn:
        for i, (envelope, payload, _) in enumerate(fixture(shape, count, version)):
            before = perf_counter()
            storage.safe_append_event(conn, envelope, payload, version)
            storage.materialize_pending(conn, AS_OF, version)
            times.append(perf_counter() - before)
            if count == 10000 and (i + 1) % 250 == 0:
                progress.append(dict(events=i + 1, append_seconds=sum(times),
                    median_ms=1000 * statistics.median(times[-64:])))
                save(f"progress-{shape}-{version}-{count}.json", progress)
                print(json.dumps(progress[-1]), flush=True)
        assert conn.execute("SELECT count(*) FROM events").fetchone()[0] == count
        assert conn.execute("SELECT log_position,event_id FROM derived_progress WHERE projector_version=?",
                            (version,)).fetchone() == (count, f"e-{count-1:06d}")
        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        assert checkpoint == (0, 0, 0)
        node_count, node_bytes = conn.execute(
            "SELECT count(*),sum(length(CAST(content AS BLOB))) FROM committed_nodes WHERE projector_version=?",
            (version,)).fetchone()
    row = dict(shape=shape, events=count, version=version, operation="append_and_publication",
               seconds=sum(times), final_window=min(64, count),
               median_ms=1000 * statistics.median(times[-64:]),
               p95_ms=1000 * sorted(times[-64:])[int(.95 * (len(times[-64:]) - 1))],
               file_bytes=path.stat().st_size, nodes=node_count, node_bytes=node_bytes,
               profiled=False)
    save(f"build-{shape}-{version}-{count}.json", row)
    return row


def append_profile():
    import sqlite3
    target = LOCAL / "profile-append.sqlite"
    with closing(sqlite3.connect(dbpath("transitions", 1000, "3"))) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    profile = cProfile.Profile()
    with closing(storage.init_db(target)) as conn:
        profile.enable()
        for i, (envelope, payload, _) in enumerate(fixture("transitions", 1064, "3")):
            if i < 1000:
                continue
            storage.safe_append_event(conn, envelope, payload, "3")
            storage.materialize_pending(conn, AS_OF, "3")
        profile.disable()
    (OUT / "append-1000-profile.txt").write_text(profile_text(profile), encoding="utf-8")
    return dict(operation="append_profile", start_depth=1000, appends=64)


def verify(shape, count, version, prototype, profile=False):
    path = dbpath(shape, count, version)
    module = verifier(prototype)
    prof = cProfile.Profile()
    before = perf_counter()
    if profile:
        prof.enable()
    report = module.verify_store(path, version)
    if profile:
        prof.disable()
    elapsed = perf_counter() - before
    assert report["ok"], report["failures"]
    assert report["event_count"] == count
    save(f"report-{shape}-{version}-{count}-{prototype}.json", report)
    paired_report_equal = None
    if prototype:
        baseline_report = OUT / f"report-{shape}-{version}-{count}-False.json"
        if baseline_report.exists():
            old = json.loads(baseline_report.read_text())
            assert old == report
            paired_report_equal = True
    row = dict(operation="whole_store_verify", shape=shape, events=count, version=version,
               prototype=prototype, seconds=elapsed, ok=report["ok"], profiled=profile,
               paired_report_equal=paired_report_equal,
               checks=report["checked"], merkle_inventory=report.get("merkle_inventory"))
    suffix = "-profile" if profile else ""
    save(f"verify-{shape}-{version}-{count}-{prototype}{suffix}.json", row)
    if profile:
        (OUT / f"verify-{shape}-{version}-{count}-{prototype}-profile.txt").write_text(
            profile_text(prof), encoding="utf-8")
    return row


def prefix_replay(shape, count, version):
    old, new = verifier(), verifier(True)
    a, b = old.Replay(version, None), new.Replay(version, None)
    elapsed = [0.0, 0.0]
    chain = ""
    for prefix, (envelope, _, data) in enumerate(fixture(shape, count, version), 1):
        raw = asdict(envelope)
        verdicts = []
        for j, replay in enumerate((a, b)):
            before = perf_counter()
            try:
                replay.append(raw, data)
                verdicts.append("pass")
            except (KeyError, ValueError, TypeError, NotImplementedError) as error:
                verdicts.append((type(error).__name__, str(error)))
            elapsed[j] += perf_counter() - before
        assert verdicts == ["pass", "pass"], (prefix, verdicts)
        assert a.records == b.records, prefix
        # These include all three roots, result_root and own lineage per prefix.
        assert a.history == b.history, prefix
        assert a.relations == b.relations, prefix
        for bid in a.records["beliefs"]:
            assert a.records["beliefs"][bid] == b.records["beliefs"][bid]
        chain = hashing._sha256_hex(chain + hashing.canonical_json(
            {"prefix": prefix, "verdict": verdicts[0], "beliefs": a.records["beliefs"]}))
        if count >= 1000 and prefix % 250 == 0:
            checkpoint = dict(operation="prefix_checkpoint", shape=shape, events=count, version=version,
                              prefixes_equal=prefix, baseline_seconds=elapsed[0],
                              prototype_seconds=elapsed[1], prefix_chain_digest=chain)
            save(f"checkpoint-prefix-{shape}-{version}-{count}.json", checkpoint)
            print(json.dumps(checkpoint), flush=True)
    assert a.history == b.history
    row = dict(operation="prefix_replay", shape=shape, events=count, version=version,
               prefixes_equal=count, baseline_seconds=elapsed[0], prototype_seconds=elapsed[1],
               speedup=elapsed[0] / elapsed[1], prefix_chain_digest=chain)
    save(f"prefix-{shape}-{version}-{count}.json", row)
    return row


def full_read(shape, count, version):
    times = []
    for _ in range(3):
        with closing(storage.open_readonly(dbpath(shape, count, version))) as conn:
            before = perf_counter()
            belief = storage.read_belief(conn, "b-000000", version)
            times.append(perf_counter() - before)
            assert len(belief["claim_candidates"]) == (count - 1 if shape != "spread" else 5)
    row = dict(operation="full_belief_read", shape=shape, events=count, version=version,
               candidates=len(belief["claim_candidates"]), seconds=times,
               median_seconds=statistics.median(times))
    save(f"read-{shape}-{version}-{count}.json", row)
    return row


def reduction(count):
    old, new = forward.Snapshot(), IndexedSnapshot()
    elapsed = [0.0, 0.0]
    windows = [[], []]
    chain = ""
    with indexed_dependencies():
        for prefix, (envelope, _, data) in enumerate(fixture("transitions", count, "3"), 1):
            snapshots = [old, new]
            verdicts = []
            for j, snapshot in enumerate(snapshots):
                before = perf_counter()
                try:
                    delta = forward.Projector().reduce(snapshot, envelope, data, AS_OF)
                    snapshots[j] = snapshot.apply(delta, prefix)
                    verdicts.append("pass")
                except (KeyError, ValueError, TypeError, NotImplementedError) as error:
                    verdicts.append((type(error).__name__, str(error)))
                duration = perf_counter() - before
                elapsed[j] += duration
                if prefix > count - 64:
                    windows[j].append(duration)
            assert verdicts == ["pass", "pass"], (prefix, verdicts)
            old, new = snapshots
            assert {k: merkle.digest(v) for k, v in old.roots.items()} == {
                k: merkle.digest(v) for k, v in new.roots.items()}, prefix
            # Root equality commits to complete members; the final complete
            # comparison below additionally checks logical reconstruction.
            chain = hashing._sha256_hex(chain + hashing.canonical_json(
                {k: merkle.digest(v) for k, v in old.roots.items()}))
        assert old.complete() == new.complete()
    row = dict(operation="in_memory_reduce_and_apply", events=count, prefixes_equal=count,
               baseline_seconds=elapsed[0], prototype_seconds=elapsed[1],
               baseline_final_median_ms=1000 * statistics.median(windows[0]),
               prototype_final_median_ms=1000 * statistics.median(windows[1]),
               prefix_chain_digest=chain)
    save(f"index-reduction-{count}.json", row)
    return row


def mixed_index():
    import replay_campaign
    from nyx import transition_dependencies
    rows = []
    for seed in (0, 17, 902467):
        evaluation = replay_campaign.AS_OF
        old, new = forward.Snapshot(), IndexedSnapshot()
        previous = None
        kinds = Counter()
        with indexed_dependencies():
            for prefix, step in enumerate(replay_campaign.generate("3", seed, 24), 1):
                envelope, _ = events.build_event(event_id=step["event_id"], event_type=step["event_type"],
                    origin_type="observed", source=step["source"], source_class="direct_observation",
                    occurred_at=step["occurred_at"], recorded_at=step["recorded_at"],
                    payload=step["data"], prev_event_hash=previous)
                previous = envelope.event_hash
                kinds[envelope.event_type] += 1
                a = forward.Projector().reduce(old, envelope, step["data"], evaluation)
                b = forward.Projector().reduce(new, envelope, step["data"], evaluation)
                assert a.nodes == b.nodes
                old, new = old.apply(a, prefix), new.apply(b, prefix)
                assert old.complete() == new.complete(), (seed, prefix)
        rows.append(dict(seed=seed, prefixes_equal=24, kinds=dict(kinds)))
    save("index-mixed-prefixes.json", rows)
    return dict(operation="mixed_index", seeds=3, prefixes_equal=72)


def mutations():
    import mutation_campaign as campaign
    results = []
    for version in ("0", "1", "2", "3"):
        folder = LOCAL / "mutations"
        folder.mkdir(parents=True, exist_ok=True)
        base = folder / f"base-{version}.db"
        campaign.build(base, version, 17, 12)
        a, b = verifier(), verifier(True)
        for index, case in enumerate(campaign.cases(base, version)):
            path = folder / f"mutant-{version}-{index}.db"
            campaign.backup(base, path)
            changed = campaign.mutate(path, version, case)
            original = a.verify_store(path, version)
            experimental = b.verify_store(path, version)
            assert original == experimental, (version, case)
            results.append(dict(projector=version, case=case, changed=changed,
                baseline_ok=original["ok"], prototype_ok=experimental["ok"],
                checks=sorted({item["check"] for item in original["failures"]}),
                failures_equal=original["failures"] == experimental["failures"]))
            # Keep full report for any baseline non-detection.
            if changed and original["ok"]:
                save(f"mutation-nondetection-{version}-{index}.json", original)
        print(f"mutation projector {version}: {len(results)} cumulative identical reports", flush=True)
    save("mutations.json", results)
    return dict(operation="mutations", cases=len(results), changed=sum(r["changed"] for r in results),
                detections=sum(r["changed"] and not r["baseline_ok"] for r in results),
                existing_nondetections=sum(r["changed"] and r["baseline_ok"] for r in results),
                controls=sum(not r["changed"] for r in results), identical_reports=len(results))


def supervise():
    OUT.mkdir(exist_ok=True)
    save("environment.json", dict(python=sys.version, executable=sys.executable,
        platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
        cpu_count=os.cpu_count(), command=sys.argv, timeout_seconds=LIMIT,
        root=str(ROOT), nyx_file=__import__("nyx").__file__))
    jobs = []
    for shape in ("concentrated", "spread"):
        for count in SIZES:
            jobs.append(["build", "--shape", shape, "--count", str(count), "--version", "2"])
            for mode in ("verify", "verify-prototype"):
                jobs.append([mode, "--shape", shape, "--count", str(count), "--version", "2"])
            jobs.append(["prefix", "--shape", shape, "--count", str(count), "--version", "2"])
            jobs.append(["read", "--shape", shape, "--count", str(count), "--version", "2"])
    for count in SIZES:
        jobs.append(["build", "--shape", "transitions", "--count", str(count), "--version", "3"])
        jobs.append(["prefix", "--shape", "transitions", "--count", str(count), "--version", "3"])
        jobs.append(["read", "--shape", "transitions", "--count", str(count), "--version", "3"])
        jobs.append(["index", "--count", str(count)])
    for mode in ("verify", "verify-prototype"):
        jobs.append([mode, "--shape", "concentrated", "--count", "500", "--version", "2", "--profile"])
    jobs.append(["mixed-index"])
    jobs.append(["append-profile"])
    jobs.append(["mutations"])
    jobs.append(["build", "--shape", "transitions", "--count", "10000", "--version", "3"])
    for i, args in enumerate(jobs):
        command = [sys.executable, "-B", str(Path(__file__).resolve()), *args]
        started = perf_counter()
        log = OUT / f"job-{i:02d}.txt"
        print(f"START {i}/{len(jobs)} {args}", flush=True)
        with log.open("w", encoding="utf-8") as output:
            try:
                result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                        timeout=LIMIT, check=False)
                row = dict(command=command, status="completed" if result.returncode == 0 else "failed",
                           returncode=result.returncode, seconds=perf_counter() - started, log=log.name)
            except subprocess.TimeoutExpired:
                row = dict(command=command, status="censored", seconds=perf_counter() - started,
                           limit_seconds=LIMIT, log=log.name)
        with (OUT / "jobs.jsonl").open("a", encoding="utf-8") as record:
            record.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["all", "build", "verify", "verify-prototype", "prefix", "read", "index", "mutations", "append-profile", "mixed-index", "smoke"])
    parser.add_argument("--shape", default="concentrated")
    parser.add_argument("--count", type=int, default=250)
    parser.add_argument("--version", default="2")
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.mode == "all":
        return supervise()
    if args.mode == "smoke":
        for shape, version in (("concentrated", "2"), ("spread", "2"), ("transitions", "3")):
            build(shape, 16, version)
            verify(shape, 16, version, False)
            verify(shape, 16, version, True)
            prefix_replay(shape, 16, version)
            full_read(shape, 16, version)
        reduction(16)
        mixed_index()
        row = dict(operation="smoke", ok=True)
    elif args.mode == "mixed-index":
        row = mixed_index()
    elif args.mode == "append-profile":
        row = append_profile()
    elif args.mode == "mutations":
        row = mutations()
    elif args.mode == "index":
        row = reduction(args.count)
    elif args.mode == "build":
        row = build(args.shape, args.count, args.version)
    elif args.mode.startswith("verify"):
        row = verify(args.shape, args.count, args.version, args.mode == "verify-prototype", args.profile)
    elif args.mode == "prefix":
        row = prefix_replay(args.shape, args.count, args.version)
    else:
        row = full_read(args.shape, args.count, args.version)
    print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
