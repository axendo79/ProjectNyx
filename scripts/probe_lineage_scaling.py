"""Standalone, deterministic workload for the ADR 0023 lineage-scaling probe.

Run from a checkout with Python 3.14; no database or pytest dependency is used.
Each independent sample starts empty, records one mention, then N agreeing
observations about one subject/property through that mention. IDs, sources,
timestamps, and payloads are fixed fixture inputs, not production defaults.

Cumulative lineage bytes count the canonical UTF-8 lineage record for each
changed belief once. This is neither total allocations nor peak memory nor
database size. Timing includes event construction, reduction, diagnostic lineage
serialization/hash verification, and snapshot application. Script startup,
printing, and final sample checks are outside the timer. Production code is not patched.
Component accounting and prefix-byte fingerprints run in a separate, untimed
sample, so the timed workload remains comparable to the original probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

# Always measure this checkout, including when launched from another directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nyx import events, hashing, reducer


START = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = {"actor_id": "sensor", "config": {}}
BELIEF_ID = "b-a"
COMPONENTS = ("claim_candidates", "event_dependencies", "identity_records")


def component_bytes(lineage: dict, total: int) -> dict[str, int]:
    """Count collection values, including brackets; keys/separators go to other."""
    counts = {name: len(hashing.canonical_json(lineage["result"][name]).encode("utf-8"))
              for name in COMPONENTS}
    counts["other"] = total - sum(counts.values())
    if counts["other"] < 0:
        raise RuntimeError("component bytes exceed complete lineage bytes")
    return counts


def sample(observations: int, *, profile: dict | None = None) -> tuple[int, float, str]:
    """Return cumulative bytes, elapsed seconds, and final lineage digest."""
    snapshot = reducer.Snapshot({})
    previous_hash = None
    cumulative_bytes = 0
    if profile is not None:
        profile["cumulative_components"] = dict.fromkeys((*COMPONENTS, "other"), 0)
        profile["prefixes"] = []
    as_of = (START + timedelta(seconds=observations + 1)).isoformat()
    started = perf_counter()
    for index in range(observations + 1):
        if index == 0:
            event_type = events.ENTITY_MENTION_RECORDED
            payload = {"mention_id": "m-a", "subject_id": "s-a",
                       "text": "the device", "link_state": "constitutive"}
        else:
            event_type = events.OBSERVATION_RECORDED
            payload = {"claims": [{
                "mention_id": "m-a", "subject_id": "s-a", "property_id": "RAM",
                "belief_id": BELIEF_ID, "claim_candidate_id": f"c-{index}",
                "value": "64GB", "verifiability": "externally_checkable",
            }]}
        envelope, payload_row = events.build_event(
            event_type=event_type, origin_type=events.ORIGIN_OBSERVED,
            source=SOURCE, source_class="direct_observation",
            occurred_at=START.isoformat(),
            recorded_at=(START + timedelta(seconds=index)).isoformat(),
            event_id=f"e-{index}", prev_event_hash=previous_hash, payload=payload,
            entity_refs=["s-a"],
        )
        delta = reducer.reduce(snapshot, envelope, json.loads(payload_row.ciphertext), as_of)
        for belief_id, belief in delta.beliefs.items():
            prior = snapshot.belief(belief_id)
            predecessors = [] if prior is None else [{
                "belief_id": belief_id, "view_version_hash": prior["view_version_hash"],
            }]
            lineage = hashing.belief_lineage(
                reducer.PROJECTOR_VERSION, envelope.event_id, envelope.event_hash,
                predecessors, belief,
            )
            material = hashing.canonical_json(lineage).encode("utf-8")
            # Fail if the diagnostic record stops matching what reduction hashed.
            if hashlib.sha256(material).hexdigest() != belief["view_version_hash"]:
                raise RuntimeError("probe lineage reconstruction differs from reducer")
            cumulative_bytes += len(material)
            if profile is not None:
                counts = component_bytes(lineage, len(material))
                for name, count in counts.items():
                    profile["cumulative_components"][name] += count
                profile["final_components"] = counts
                profile["final_lineage_bytes"] = len(material)
        snapshot = snapshot.apply(delta, index + 1)
        if profile is not None:
            profile["prefixes"].append({
                "position": snapshot.log_position,
                "event_id": snapshot.event_id,
                "snapshot_sha256": hashlib.sha256(
                    hashing.canonical_json(snapshot.complete()).encode("utf-8")
                ).hexdigest(),
                "belief_lineage": {key: value["view_version_hash"]
                                   for key, value in snapshot.beliefs().items()},
            })
        previous_hash = envelope.event_hash
    elapsed = perf_counter() - started

    belief = snapshot.belief(BELIEF_ID)
    if (snapshot.log_position != observations + 1
            or len(belief["claim_candidates"]) != observations
            or len(reducer.evidence_event_ids(belief["claim_candidates"])) != observations):
        raise RuntimeError("probe did not retain the expected observations/candidates")
    return cumulative_bytes, elapsed, belief["view_version_hash"]


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=positive_int, default=[32, 64, 128])
    parser.add_argument("--repeat", type=positive_int, default=3,
                        help="independent runs per size; report median time (default: 3)")
    parser.add_argument("--json", type=Path, help="write measurements and every-prefix byte fingerprints")
    args = parser.parse_args()
    print(f"Python {platform.python_version()} | {platform.platform()}")
    print(f"Projector {reducer.PROJECTOR_VERSION} | {args.repeat} runs per size | MB = 1,000,000 bytes")
    print("observations  cumulative_lineage_bytes  lineage_MB  median_seconds")
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "projector_version": reducer.PROJECTOR_VERSION, "repeat": args.repeat,
              "samples": []}
    for size in args.sizes:
        runs = [sample(size) for _ in range(args.repeat)]
        if len({(byte_count, digest) for byte_count, _, digest in runs}) != 1:
            raise RuntimeError("fixed workload produced non-deterministic lineage")
        byte_count = runs[0][0]
        median_seconds = statistics.median(seconds for _, seconds, _ in runs)
        print(f"{size:12d}  {byte_count:24d}  {byte_count / 1_000_000:10.6f}  {median_seconds:14.6f}")
        profile = {}
        profiled_bytes, _, digest = sample(size, profile=profile)
        if (profiled_bytes, digest) != (byte_count, runs[0][2]):
            raise RuntimeError("profiled sample differs from timed workload")
        if sum(profile["cumulative_components"].values()) != byte_count:
            raise RuntimeError("component accounting does not reconcile")
        print("  cumulative components: " + ", ".join(
            f"{name}={count} ({100 * count / byte_count:.2f}%)"
            for name, count in profile["cumulative_components"].items()))
        print("  final record components: " + ", ".join(
            f"{name}={count}" for name, count in profile["final_components"].items()))
        report["samples"].append({"observations": size, "cumulative_lineage_bytes": byte_count,
                                  "seconds": [run[1] for run in runs],
                                  "median_seconds": median_seconds, "final_lineage": digest,
                                  **profile})
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
