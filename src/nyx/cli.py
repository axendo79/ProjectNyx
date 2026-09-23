"""Read-only inspection of shipped Nyx stores; no implicit publication or repair."""

import argparse
from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timezone
import json
import sys

from . import integrity, projection, storage
from .timestamps import validate_timestamp


def _timestamp(value):
    try:
        validate_timestamp(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def _limit(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("limit must be a nonnegative integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("limit must be a nonnegative integer")
    return number


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("belief", "subject", "mention", "replay", "verify", "status", "events"):
        command = commands.add_parser(name)
        command.add_argument("--db", required=True, help="existing SQLite store; no default path")
        command.add_argument("--json", action="store_true", help="emit machine-readable JSON")
        if name not in ("events", "status"):
            command.add_argument("--projector", default="0", choices=sorted(projection.PROJECTORS),
                                 help='projector version (default: "0"; identity reads require "1"/"2")')
        if name in ("belief", "subject", "replay"):
            command.add_argument("--as-of", type=_timestamp, help="inclusive recorded_at cutoff")
        if name in ("belief", "subject", "mention"):
            command.add_argument(name + "_id")
        if name == "subject":
            command.add_argument("--property", help="exact opaque property ID")
        if name == "events":
            command.add_argument("--limit", type=_limit)
            command.add_argument("--since", type=_timestamp, help="inclusive recorded_at lower bound")
    return parser


def _identity_version(version):
    if not isinstance(projection.PROJECTORS[version], projection.ReducerProjector):
        raise NotImplementedError(f"typed identity reads are unimplemented for projector {version!r}")


def _replay(conn, version, as_of):
    log = storage.read_all_events(conn)
    if isinstance(projection.PROJECTORS[version], projection.ReducerProjector):
        return projection.project_snapshot(log, as_of, version).complete()
    return {"beliefs": projection.project(log, as_of, version)}


def _run(conn, args):
    name = args.command
    if name == "status":
        metadata = storage.read_store_metadata(conn)
        return {**metadata, "freshness": {
            version: storage.read_projection_status(conn, version)
            for version in metadata["projector_versions"]}}
    if name == "events":
        # Validate the full log before filtering. Payloads are never emitted.
        log = storage.read_all_events(conn)
        since = None if args.since is None else datetime.fromisoformat(args.since)
        envelopes = [asdict(env) for env, _ in log
                     if since is None or datetime.fromisoformat(env.recorded_at) >= since]
        if args.limit is not None:
            envelopes = envelopes[:args.limit]
        return {"read_mode": "log", "events": envelopes, "returned_count": len(envelopes)}
    version = args.projector
    if name == "verify":
        count = sum(1 for _ in integrity.verified_log(storage.read_all_events(conn)))
        return {"result": "PASS", "event_count": count,
                "verification_scope": "full log envelope, payload and predecessor integrity; no reducer audit"}
    if name == "mention":
        _identity_version(version)
        return {"read_mode": "materialized", **storage.read_mention_status(conn, args.mention_id, version)}
    if name == "replay":
        at = args.as_of or datetime.now(timezone.utc).isoformat()
        return {"read_mode": "replay", "as_of": at, "view": _replay(conn, version, at),
                "materialized_status": storage.read_projection_status(conn, version)}
    if name == "belief":
        status = storage.read_belief_status(conn, args.belief_id, version)
        if args.as_of is None:
            return {"read_mode": "materialized", **status}
        view = storage.evaluate_whole_view(conn, args.as_of, version)
        return {"read_mode": "replay", "as_of": args.as_of,
                "belief": view.get(args.belief_id),
                "materialized_status": {key: value for key, value in status.items() if key != "belief"}}
    _identity_version(version)
    status = storage.read_entity_status(conn, args.subject_id, version)
    if args.as_of is not None:
        snapshot = projection.project_snapshot(storage.read_all_events(conn), args.as_of, version)
        result = {"read_mode": "replay", "as_of": args.as_of,
                  "record": snapshot.record("entities", args.subject_id),
                  "materialized_status": {key: value for key, value in status.items() if key != "record"}}
    else:
        snapshot = storage.read_snapshot(conn, version)
        result = {"read_mode": "materialized", **status}
    result["beliefs"] = {key: belief for key, belief in snapshot.beliefs().items()
        if belief["subject_id"] == args.subject_id
        and (args.property is None or belief["property_id"] == args.property)}
    return result


def _human(value, indent=0):
    """Plain recursive text keeps all returned status and record fields visible."""
    prefix = " " * indent
    if isinstance(value, dict):
        if not value:
            return [prefix + "(empty)"]
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(prefix + f"{key}:")
                lines.extend(_human(item, indent + 2))
            else:
                label = "unknown" if key == "stale" and item is None else json.dumps(item, ensure_ascii=False)
                lines.append(prefix + f"{key}: {label}")
        return lines
    if isinstance(value, list):
        if not value:
            return [prefix + "(empty)"]
        lines = []
        for item in value:
            lines.append(prefix + "-")
            lines.extend(_human(item, indent + 2))
        return lines
    return [prefix + json.dumps(value, ensure_ascii=False)]


def main(argv=None):
    from .writer import ClockSkewError
    args = _parser().parse_args(argv)
    result = {"command": args.command}
    if hasattr(args, "projector"):
        result["projector_version"] = args.projector
    code = 0
    try:
        with closing(storage.open_readonly(args.db)) as conn:
            # One locked read snapshot covers content and its freshness disclosure.
            with conn:
                conn.execute("BEGIN")
                result.update(_run(conn, args))
    except ClockSkewError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except NotImplementedError as exc:
        result.update(result="unimplemented", reason=str(exc))
        code = 2
    # IntegrityError deliberately propagates with its precise type and message.
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("\n".join(_human(result)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
