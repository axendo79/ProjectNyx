"""Standalone, deterministic workload for the ADR 0023 lineage-scaling probe.

Run from a checkout with Python 3.14; no pytest dependency is used. Select
--projector-version 1 or 2; --database adds a separate SQLite write measurement.
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
Publication material counts serialized changed records for version 1, or emitted
tree nodes, compact headers, and changed root descriptors for version 2. It
excludes Layer A, progress rows, SQL/index overhead, and filesystem write amplification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

# Always measure this checkout, including when launched from another directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nyx import committed, committed_storage, events, hashing, reducer, storage


START = datetime(2026, 7, 13, tzinfo=timezone.utc)
SOURCE = {"actor_id": "sensor", "config": {}}
BELIEF_ID = "b-a"
COMPONENTS = ("claim_candidates", "event_dependencies", "identity_records")


def component_bytes(lineage: dict, total: int) -> dict[str, int]:
    """Count collection values, including brackets; keys/separators go to other."""
    collections = lineage.get("collection_roots", lineage["result"])
    counts = {name: len(hashing.canonical_json(collections[name]).encode("utf-8"))
              for name in COMPONENTS}
    counts["other"] = total - sum(counts.values())
    if counts["other"] < 0:
        raise RuntimeError("component bytes exceed complete lineage bytes")
    return counts


def workload(observations):
    """Yield the identical recorded workload for either projector or storage path."""
    previous_hash = None
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
        yield envelope, payload_row
        previous_hash = envelope.event_hash


def sample(observations: int, *, profile: dict | None = None,
           projector_version: str = "1") -> tuple[int, float, str]:
    """Return cumulative outer lineage bytes, elapsed seconds and final digest."""
    if projector_version not in ("1", "2"):
        raise ValueError("probe requires projector 1 or 2")
    implementation = reducer if projector_version == "1" else committed
    snapshot = reducer.Snapshot({}) if projector_version == "1" else committed.Snapshot()
    cumulative_bytes = 0
    if profile is not None:
        profile["cumulative_components"] = dict.fromkeys((*COMPONENTS, "other"), 0)
        profile["prefixes"] = []
        profile["cumulative_publication_bytes"] = 0
        profile["cumulative_node_bytes"] = 0
        profile["cumulative_new_nodes"] = 0
    as_of = (START + timedelta(seconds=observations + 1)).isoformat()
    started = perf_counter()
    for index, (envelope, payload_row) in enumerate(workload(observations)):
        delta = implementation.reduce(snapshot, envelope, json.loads(payload_row.ciphertext), as_of)
        for belief_id, belief in delta.beliefs.items():
            prior = (snapshot.belief(belief_id) if projector_version == "1"
                     else snapshot.header(belief_id))
            predecessors = [] if prior is None else [{
                "belief_id": belief_id, "view_version_hash": prior["view_version_hash"],
            }]
            lineage = (hashing.belief_lineage("1", envelope.event_id, envelope.event_hash,
                                             predecessors, belief) if projector_version == "1"
                       else committed.lineage(envelope.event_id, envelope.event_hash, predecessors, belief))
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
            if projector_version == "2":
                material = committed_storage.publication_material(delta)
                node_bytes = sum(len(raw.encode("utf-8")) for raw in delta.nodes.values())
                profile["cumulative_node_bytes"] += node_bytes
                profile["cumulative_new_nodes"] += len(delta.nodes)
                profile["final_node_bytes"] = node_bytes
                profile["final_new_nodes"] = len(delta.nodes)
            else:
                material = (hashing.canonical_json(value) for kind in reducer.RECORD_KINDS
                            for value in getattr(delta, kind).values())
            publication_bytes = sum(len(raw.encode("utf-8")) for raw in material)
            profile["cumulative_publication_bytes"] += publication_bytes
            profile["final_publication_bytes"] = publication_bytes
            complete = snapshot.complete()
            logical = {**complete, "beliefs": {
                key: {k: v for k, v in belief.items() if k != "view_version_hash"}
                for key, belief in complete["beliefs"].items()}}
            profile["prefixes"].append({
                "position": snapshot.log_position,
                "event_id": snapshot.event_id,
                "snapshot_sha256": hashlib.sha256(
                    hashing.canonical_json(complete).encode("utf-8")
                ).hexdigest(),
                "logical_snapshot_sha256": hashlib.sha256(
                    hashing.canonical_json(logical).encode("utf-8")).hexdigest(),
                "belief_lineage": {key: value["view_version_hash"]
                                   for key, value in snapshot.beliefs().items()},
            })
    elapsed = perf_counter() - started

    belief = snapshot.belief(BELIEF_ID)
    if (snapshot.log_position != observations + 1
            or len(belief["claim_candidates"]) != observations
            or len(reducer.evidence_event_ids(belief["claim_candidates"])) != observations):
        raise RuntimeError("probe did not retain the expected observations/candidates")
    return cumulative_bytes, elapsed, belief["view_version_hash"]


def database_sample(observations, projector_version):
    """Real SQLite append/validation/publication, fresh file, normal WAL settings.

    Database initialization and final reads are excluded. Each event has the
    separate append and derived transactions used by the production write path.
    """
    as_of = (START + timedelta(seconds=observations + 1)).isoformat()
    with tempfile.TemporaryDirectory(prefix="nyx-lineage-") as folder:
        with closing(storage.init_db(Path(folder) / "probe.db", create=True)) as conn:
            started = perf_counter()
            for envelope, payload in workload(observations):
                storage.safe_append_event(conn, envelope, payload, projector_version)
                storage.materialize_pending(conn, as_of, projector_version)
            elapsed = perf_counter() - started
            belief = storage.read_belief(conn, BELIEF_ID, projector_version)
            if belief["stale"] or len(belief["claim_candidates"]) != observations:
                raise RuntimeError("database probe lost candidates or publication progress")
            return elapsed, belief["view_version_hash"]


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
    parser.add_argument("--projector-version", choices=("1", "2"), default="1")
    parser.add_argument("--database", action="store_true", help="also time real SQLite writes in separate runs")
    args = parser.parse_args()
    print(f"Python {platform.python_version()} | {platform.platform()}")
    print(f"Projector {args.projector_version} | {args.repeat} runs per size | MB = 1,000,000 bytes")
    if args.projector_version == "2":
        print("Lineage components count root strings; publication bytes include new tree nodes and compact headers.")
    print("observations  cumulative_lineage_bytes  lineage_MB  median_seconds")
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "projector_version": args.projector_version, "repeat": args.repeat,
              "samples": []}
    for size in args.sizes:
        runs = [sample(size, projector_version=args.projector_version) for _ in range(args.repeat)]
        if len({(byte_count, digest) for byte_count, _, digest in runs}) != 1:
            raise RuntimeError("fixed workload produced non-deterministic lineage")
        byte_count = runs[0][0]
        median_seconds = statistics.median(seconds for _, seconds, _ in runs)
        print(f"{size:12d}  {byte_count:24d}  {byte_count / 1_000_000:10.6f}  {median_seconds:14.6f}")
        profile = {}
        profiled_bytes, _, digest = sample(size, profile=profile, projector_version=args.projector_version)
        if (profiled_bytes, digest) != (byte_count, runs[0][2]):
            raise RuntimeError("profiled sample differs from timed workload")
        if sum(profile["cumulative_components"].values()) != byte_count:
            raise RuntimeError("component accounting does not reconcile")
        print("  cumulative components: " + ", ".join(
            f"{name}={count} ({100 * count / byte_count:.2f}%)"
            for name, count in profile["cumulative_components"].items()))
        print("  final record components: " + ", ".join(
            f"{name}={count}" for name, count in profile["final_components"].items()))
        print(f"  publication bytes: cumulative={profile['cumulative_publication_bytes']}, "
              f"final={profile['final_publication_bytes']}; "
              f"cumulative new-node bytes={profile['cumulative_node_bytes']}")
        if args.database:
            database_runs = [database_sample(size, args.projector_version) for _ in range(args.repeat)]
            if any(database_digest != digest for _, database_digest in database_runs):
                raise RuntimeError("database lineage differs from in-memory reduction")
            profile["database_seconds"] = [seconds for seconds, _ in database_runs]
            profile["database_median_seconds"] = statistics.median(profile["database_seconds"])
            print(f"  SQLite median seconds: {profile['database_median_seconds']:.6f}")
        report["samples"].append({"observations": size, "cumulative_lineage_bytes": byte_count,
                                  "seconds": [run[1] for run in runs],
                                  "median_seconds": median_seconds, "final_lineage": digest,
                                  **profile})
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
