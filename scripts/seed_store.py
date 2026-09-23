"""Create one persistent, inspectable fixture using the shipped public write path.

Projector 2 has identity/candidates and an unpublished final belief; projector 0
has legacy corrections. They never share a log. IDs and event inputs are fixed
unless --seed selects a reproducible randomized fixture. SQLite initialization
and operational diagnostic timestamps still use the production clock. Event
assignment uses an injected fixture clock; this is not a historical-import API.
"""

import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nyx import events, immune, ingestion, projection, storage, writer


MIN_OBSERVATIONS = 8
START = datetime(2026, 7, 13, tzinfo=timezone.utc)


def _create_target(path, force):
    path = Path(path).absolute()
    if path.is_symlink():
        raise ValueError(f"refusing symbolic-link database target: {path}")
    if path.exists() and not force:
        raise FileExistsError(f"store already exists: {path}; use --force to replace it")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise FileExistsError("SQLite sidecars exist; close readers/writers and resolve recovery before replacing the store")
    if path.exists():
        if not path.is_file():
            raise ValueError(f"database target is not a regular file: {path}")
        path.unlink()  # Only the explicitly named --force target; never recursive.
    path.parent.mkdir(parents=True, exist_ok=True)
    # Reserve exclusively so a concurrent creator cannot be silently overwritten.
    with path.open("xb"):
        pass
    return path


def seed_store(db, observations=MIN_OBSERVATIONS, projector="0", *, force=False, seed=None):
    if projector not in ("0", "2"):
        raise ValueError("fixture projector must be 0 or 2")
    if type(observations) is not int or observations < MIN_OBSERVATIONS:
        raise ValueError(f"observations must be at least {MIN_OBSERVATIONS} to retain the complete fixture structure")
    path = _create_target(db, force)
    prefix = "demo" if seed is None else f"demo-{seed}"
    rng = None if seed is None else random.Random(seed)
    names = ("alpha", "beta", "gamma")
    properties = ("ram", "model")
    beliefs = [f"{prefix}:{name}:{prop}" for name in names for prop in properties]
    manifest = {"db": str(path), "projector": projector, "observation_count": observations,
                "subject_ids": [], "belief_ids": list(beliefs), "mention_ids": [],
                "property_ids": ["ram", "model", "temperature"] if projector == "2" else [],
                "source_actor_id": f"{prefix}:fixture",
                "candidate_ids": [], "event_ids": [], "published_belief": beliefs[2],
                "unpublished_belief": None, "corrected_belief": None}
    source = {"actor_id": f"{prefix}:fixture", "config": {}}
    source_class = "direct_observation"
    counter = 0

    def next_event():
        nonlocal counter
        counter += 1
        event_id = f"{prefix}-p{projector}-e{counter:03d}"
        manifest["event_ids"].append(event_id)
        return {"event_id": event_id, "recorded_at": (START + timedelta(seconds=counter)).isoformat()}

    with closing(storage.init_db(path, create=True,
            clock=lambda: (START + timedelta(seconds=counter)).isoformat(),
            threshold=timedelta(seconds=120))) as conn:
        if projector == "2":
            for name in names:
                subject, mid = f"{prefix}:s-{name}", f"{prefix}:m-{name}"
                manifest["subject_ids"].append(subject)
                manifest["mention_ids"].append(mid)
                stamp = next_event()
                pair = ingestion.prepare_mention(conn, subject_id=subject, mention_id=mid,
                    text=f"fixture device {name}", source=source, source_class=source_class,
                    origin_type=events.ORIGIN_OBSERVED, occurred_at=stamp["recorded_at"],
                    event_id=stamp["event_id"])
                ingestion.submit(conn, pair, stamp["recorded_at"], "2")

        def observe(name, prop, value, *, pending=False, correction=False):
            stamp = next_event()
            at = stamp["recorded_at"]
            bid = f"{prefix}:{name}:{prop}"
            if projector == "2":
                cid = f"{prefix}:c-{counter:03d}"
                manifest["candidate_ids"].append(cid)
                claim = {"belief_id": bid, "subject_id": f"{prefix}:s-{name}",
                         "mention_id": f"{prefix}:m-{name}", "property_id": prop,
                         "claim_candidate_id": cid, "value": value,
                         "verifiability": "externally_checkable"}
                pair = ingestion.prepare_observation(conn, claims=[claim], source=source,
                    source_class=source_class, occurred_at=at, projector_version="2",
                    event_id=stamp["event_id"])
            else:
                raw = {"belief_id": bid, "value": value, "verifiability": "externally_checkable",
                       "occurred_at": at, "source": source, "source_class": source_class}
                checked = immune.stage1_schema_validate(raw)
                if not checked.accepted:
                    raise ValueError(f"immune stage 1 rejected fixture: {checked.reason}")
                kind = events.CORRECTION_APPENDED if correction else events.OBSERVATION_RECORDED
                projection.assert_not_backdated(storage.read_belief(conn, bid, "0"), kind, at)
                pair = writer.prepare_event(event_type=kind, origin_type=events.ORIGIN_OBSERVED,
                    source=source, source_class=source_class, occurred_at=at,
                    payload={key: raw[key] for key in ("belief_id", "value", "verifiability")},
                    event_id=stamp["event_id"])
            # The final p2 event commits normally. Its recording time is beyond
            # this explicit evaluation cutoff, so submit leaves it unpublished.
            cutoff = (START + timedelta(seconds=counter - 1)).isoformat() if pending else at
            ingestion.submit(conn, pair, cutoff, projector)

        for index, name in enumerate(names):
            ram = ("16GB", "32GB", "64GB")[index] if rng is None else rng.choice(("16GB", "32GB", "64GB"))
            observe(name, "ram", ram)
            observe(name, "model", f"device-{index + 1}" if rng is None else f"device-{rng.randrange(1, 1000)}")
        # Re-observations vary candidates in p2, or the current scalar value in p0.
        # 128GB differs from every initial RAM value, even with a supplied seed.
        for index in range(observations - 6 - (projector == "2")):
            observe("alpha", "ram", "128GB" if index % 2 == 0 else "256GB")
        if projector == "2":
            manifest["unpublished_belief"] = f"{prefix}:gamma:temperature"
            manifest["belief_ids"].append(manifest["unpublished_belief"])
            observe("gamma", "temperature", "21C", pending=True)
        else:
            manifest["corrected_belief"] = f"{prefix}:alpha:ram"
            observe("alpha", "ram", "512GB", correction=True)
        manifest["event_count"] = len(manifest["event_ids"])
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--projector", choices=("0", "2"), default="0")
    parser.add_argument("--observations", type=int, default=MIN_OBSERVATIONS,
                        help=f"total observation events, excluding mentions/correction (minimum/default {MIN_OBSERVATIONS})")
    parser.add_argument("--force", action="store_true", help="replace the named store; close all connections first")
    parser.add_argument("--seed", type=int, help="reproducible randomized values and a seed-specific ID namespace")
    args = parser.parse_args(argv)
    if args.observations < MIN_OBSERVATIONS:
        parser.error(f"--observations must be at least {MIN_OBSERVATIONS}")
    try:
        result = seed_store(args.db, args.observations, args.projector, force=args.force, seed=args.seed)
    except writer.ClockSkewError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
