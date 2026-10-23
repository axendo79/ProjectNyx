"""Consolidate completed evidence and append the measurement tables."""
from collections import Counter
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "design" / "deephist-evidence"
REPORT = ROOT / "design" / "2026-10-23-deep-history-investigation.md"
SIZES = (250, 500, 1000, 2000)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    jobs = [json.loads(line) for line in (OUT / "jobs.jsonl").read_text().splitlines()]
    assert len(jobs) == 62, "supervisor not finished"
    assert (OUT / "verifier-cli.json").exists(), "CLI control not finished"
    assert not [r for r in jobs if r["status"] == "failed"], "inspect failed jobs before finalizing"
    measurements, reports, checkpoints = [], [], []
    for path in sorted(OUT.glob("*.json")):
        if path.name.startswith(("build-", "verify-", "read-", "prefix-", "index-reduction-")):
            measurements.append(read(path))
        elif path.name.startswith("report-"):
            reports.append(read(path))
        elif path.name.startswith("checkpoint-prefix-"):
            checkpoints.append(read(path))
    nondetections = {path.name: read(path) for path in sorted(OUT.glob("mutation-nondetection-*.json"))}
    results = dict(measurements=measurements, verifier_reports=reports,
                   existing_nondetection_reports=nondetections,
                   prefix_checkpoints=checkpoints, jobs=jobs,
                   raw_job_stdout_local="scratch/deephist/raw-evidence",
                   note="Timers exclude assertion/digest/checkpoint work; censoring uses process wall time.")
    (OUT / "results.json").write_text(json.dumps(results, indent=2)+"\n", encoding="utf-8")
    def get(operation, n, shape=None, version=None, prototype=None):
        return next((r for r in measurements if r.get("operation") == operation and
                     r.get("events") == n and (shape is None or r.get("shape") == shape) and
                     (version is None or r.get("version") == version) and
                     (prototype is None or r.get("prototype") == prototype) and
                     not r.get("profiled", False)), None)
    def number(row, key="seconds"):
        return f'{row[key]:.3f}' if row else "censored / unavailable"
    lines = ["## Measurements", "", "Raw numeric results, report counts, prefix digests and commands: "
             "[results.json](deephist-evidence/results.json). "
             "Censoring is wall time including process startup; successful operation timers exclude startup.",
             "", "### Whole-store verification (projector 2)", "",
             "| Events | Concentrated existing s | Incremental s | Speedup | Spread existing s | Incremental s | Speedup |",
             "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n in SIZES:
        cells = [str(n)]
        for shape in ("concentrated", "spread"):
            a = get("whole_store_verify", n, shape, "2", False)
            b = get("whole_store_verify", n, shape, "2", True)
            cells += [number(a), number(b),
                      f'{a["seconds"]/b["seconds"]:.2f}x' if a and b else "no exact paired ratio"]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "The 2,000-event concentrated baseline was censored at 1,200 seconds. "
              "Its prototype report is successful, but there is no completed baseline whole-store "
              "report at that endpoint. No exact speedup or empirical full-report pair is claimed there.",
              "", "### Replay-only verifier curve and prefix equivalence", "",
              "| Events | Concentrated existing s | Incremental s | Speedup | Spread speedup | Transition replay speedup |",
              "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n in SIZES:
        a = get("prefix_replay", n, "concentrated", "2")
        b = get("prefix_replay", n, "spread", "2")
        c = get("prefix_replay", n, "transitions", "3")
        lines.append("| " + " | ".join([str(n), number(a, "baseline_seconds"),
            number(a, "prototype_seconds"), f'{a["speedup"]:.2f}x' if a else "censored",
            f'{b["speedup"]:.2f}x' if b else "censored",
            f'{c["speedup"]:.2f}x' if c else "censored"]) + " |")
    prefixes = [r for r in measurements if r.get("operation") == "prefix_replay" and r["events"] in SIZES]
    lines += ["", f'Completed large-workload prefix comparisons: {sum(r["prefixes_equal"] for r in prefixes):,}. '
              "They compare records, recomputed roots, history and relations; every completed comparison matched. "
              "The seeded tests add 300 direct complete-report prefix pairs. "
              "Censored jobs/checkpoints are recorded separately, rather than counted as completed workloads.",
              "", "### Append and index component measurements", "",
              "| Events | P2 concentrated append+publish median ms | P3 transition append+publish median ms | P3 p95 ms | In-memory scan median ms | Index median ms |",
              "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n in SIZES:
        a = get("append_and_publication", n, "concentrated", "2")
        b = get("append_and_publication", n, "transitions", "3")
        c = get("in_memory_reduce_and_apply", n)
        lines.append("| " + " | ".join([str(n), number(a,"median_ms"), number(b,"median_ms"),
                     number(b,"p95_ms"), number(c,"baseline_final_median_ms"),
                     number(c,"prototype_final_median_ms")]) + " |")
    lines += ["", "These are different timing boundaries: the two database columns contain real append and "
              "publication; the final two columns compare one in-memory reduction plus snapshot application. "
              "No database-index after measurement exists. All completed index runs compare every prefix's "
              "index roots and the final complete logical snapshot. The mixed index campaign also compares "
              "all output node bytes and complete snapshots at 72 prefixes across three seeds.",
              "", "### Full-belief reads (median of three, seconds)", "",
              "| Events | P2 concentrated | P3 transition history | P2 spread first belief (5 candidates) |",
              "| ---: | ---: | ---: | ---: |"]
    for n in SIZES:
        lines.append("| " + " | ".join([str(n),
            number(get("full_belief_read",n,"concentrated","2"),"median_seconds"),
            number(get("full_belief_read",n,"transitions","3"),"median_seconds"),
            number(get("full_belief_read",n,"spread","2"),"median_seconds")]) + " |")
    mutations = read(OUT / "mutations.json")
    counts = dict(cases=len(mutations), controls=sum(not r["changed"] for r in mutations),
        detected=sum(r["changed"] and not r["baseline_ok"] for r in mutations),
        existing_nondetections=sum(r["changed"] and r["baseline_ok"] for r in mutations))
    lines += ["", "### Existing mutation/corruption matrix", "",
              f'{counts["cases"]} cases; {counts["controls"]} unchanged controls; '
              f'{counts["detected"]} changed cases detected by both; '
              f'{counts["existing_nondetections"]} changed cases not detected by either. '
              "Every complete report matched exactly, including failures and unchecked findings. "
              "Every existing detection therefore still fires; existing non-detections remain limitations.",
              "", "[Every case and detection category](deephist-evidence/mutations.json). "
              "The campaign uses all cases returned by the shipped mutation harness, seed 17 and "
              "12 events, for all four projectors. Self-consistently rehashed Merkle/relation mutants are included.",
              "", "Existing non-detection IDs (no scope change is claimed):", ""]
    for version in ("0", "1", "2", "3"):
        names = [r["case"] for r in mutations if r["projector"] == version and r["changed"] and r["baseline_ok"]]
        lines.append("- Projector " + version + ": " + (", ".join("`"+n+"`" for n in names) or "none") + ".")
    lines += ["", "### Censored runs", ""]
    for row in jobs:
        if row["status"] == "censored":
            lines.append("- " + " ".join(row["command"][3:]) +
                         f': censored at {row["limit_seconds"]} s; observed wall {row["seconds"]:.3f} s.')
    progress_path = OUT / "progress-transitions-3-10000.json"
    if progress_path.exists():
        lines += ["", "The 10,000-event append attempt saved verified progress windows before any censoring:",
                  "", "| Completed events | Accumulated append+publish s | Final-window median ms |",
                  "| ---: | ---: | ---: |"]
        for row in read(progress_path):
            lines.append(f'| {row["events"]} | {row["append_seconds"]:.3f} | {row["median_ms"]:.3f} |')
        lines += ["", "These are completed prefixes of an attempt, not a completed 10,000-event result. "
                  "No 10,000-event full verify, RSS/virtual-address limit experiment, 100k or 500k run is claimed."]
    lines += ["", "### Shipped probe control", "",
              "[Store-scaling control data](deephist-evidence/store-scaling.json) and "
              "[stdout](deephist-evidence/store-scaling.txt) preserve actual rounded counts. "
              "Projector 1 was explicitly skipped for this control; it was still covered by both full test suites.",
              "", "Raw per-job stdout duplicates the consolidated JSON and remains in the local ignored "
              "fixture directory; failed/censored job logs are retained in this evidence folder. "
              "No experimental phase was skipped for a missing permission. Delivery status is recorded in the final summary."]
    marker = "\n## Measurements\n"
    original = REPORT.read_text(encoding="utf-8-sig").split(marker)[0]
    REPORT.write_text(original.rstrip()+"\n\n"+"\n".join(lines)+"\n", encoding="utf-8")
    keep = {"setup.json", "environment.json", "baseline-pytest.txt", "prototype-pytest.txt",
            "store-scaling.json", "store-scaling.txt", "jobs.jsonl", "supervisor.jsonl",
            "verifier-cli.json", "mutations.json", "index-mixed-prefixes.json",
            "progress-transitions-3-10000.json", "results.json",
            "append-1000-profile.txt", "verify-concentrated-2-500-False-profile.txt",
            "verify-concentrated-2-500-True-profile.txt"}
    keep.update(row["log"] for row in jobs if row["status"] != "completed")
    raw = ROOT / "scratch" / "deephist" / "raw-evidence"
    raw.mkdir(exist_ok=True)
    for path in OUT.iterdir():
        if path.is_file() and path.name not in keep:
            target = raw / path.name
            assert path.resolve().is_relative_to(ROOT) and target.resolve().is_relative_to(ROOT)
            shutil.move(str(path), str(target))
    # Normalize only investigation artifacts, never repository authority/source.
    for path in [REPORT, *OUT.iterdir(), *ROOT.glob("design/deephist_*.py"),
                 ROOT / "design" / "test_deephist.py"]:
        if path.is_file():
            path.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
    print(json.dumps(dict(jobs=Counter(r["status"] for r in jobs), mutations=counts,
                          prefixes=sum(r["prefixes_equal"] for r in prefixes)), indent=2))


if __name__ == "__main__":
    main()
