"""Layer A storage — the append-only Reality Layer, and derived-table access.

spec/NYX_ARCHITECTURE.md §1 (substrate, write path) and
spec/NYX_V0_IMPLEMENTATION.md §4 (schema). The append is THE durable commit
(Invariant 8) — everything else is a reconstructible derivative.

Append-only is engine-enforced (UPDATE/DELETE triggers in schema.sql), not a
convention (Invariant 1). `safe_append_event` is the sole write path into Layer A;
it inserts the envelope and payload with append freshness in one transaction.
Version 0 uses entity_event_index; versions 1/2 use identity_event_index and
belief_event_index. Derived publication and its progress commit separately.
"""

from __future__ import annotations

import json
import re
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path

from . import hashing, projection, committed, committed_storage, integrity
from .events import Envelope, Payload
from .projection import _instant
from .reducer import EventDelta, RECORD_KINDS, SUPPORTED_EVENTS

# schema.sql lives at the repo root: src/nyx/storage.py -> parents[2].
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"

_EVENT_COLUMNS = (
    "event_id", "idempotency_key", "schema_version", "event_type",
    "occurred_at", "recorded_at", "source", "source_class", "origin_type",
    "payload_hash", "entity_refs", "prev_event_hash", "event_hash",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DATABASE_SCHEMA_VERSION = 4  # ADR 0025; older databases refuse unchanged.
# Initialization diagnostics, not an identity or compatibility signal.
CREATED_BY = "nyx/0.0.0"


class SchemaCompatibilityError(RuntimeError):
    """ADR 0011 refusal, with a stable classification for diagnostics."""

    def __init__(self, reason: str, detail: str):
        self.reason = reason
        super().__init__(f"{reason}: {detail}")


# Ignore comments, whitespace, keyword case and identifier quoting when
# comparing CHECK expressions. Quoted text must not supply decoy constraints.
_SQL_TOKEN = re.compile(
    r"--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|"
    r"`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]",
    re.DOTALL,
)


def _check_constraints(sql: str) -> list[tuple[str, ...]]:
    tokens = [m.group() for m in _SQL_TOKEN.finditer(sql)
              if not m.group().startswith(("--", "/*"))]
    checks = []
    for index, token in enumerate(tokens):
        if token.lower() != "check" or tokens[index + 1:index + 2] != ["("]:
            continue
        depth = 1
        expression = []
        for part in tokens[index + 2:]:
            if part == "(":
                depth += 1
            elif part == ")":
                depth -= 1
            if depth == 0:
                break
            if part.startswith(('"', "`", "[")):
                part = part[1:-1]
            expression.append(part if part.startswith("'") else part.lower())
        if depth:
            raise SchemaCompatibilityError("malformed_metadata", "unterminated CHECK constraint")
        checks.append(tuple(expression))
    return sorted(checks)


class BackdatedRecordingError(ValueError):
    """ADR 0010: a new event cannot precede the log tip's recording time."""


def _validate_schema(conn: sqlite3.Connection) -> None:
    """Inspect metadata without modifying it (ADR 0011)."""
    meta = conn.execute(
        "SELECT type, sql FROM sqlite_master WHERE name = 'schema_meta'"
    ).fetchone()
    if meta is None:
        raise SchemaCompatibilityError("missing_metadata", "schema_meta is absent")
    if meta[0] != "table":
        raise SchemaCompatibilityError("malformed_metadata", "schema_meta is not a table")
    columns = conn.execute("PRAGMA table_xinfo(schema_meta)").fetchall()
    if [column[1] for column in columns] != ["id", "version", "created_at", "created_by"]:
        raise SchemaCompatibilityError("malformed_metadata", "schema_meta must have four fields")
    if any(column[6] != 0 for column in columns):
        raise SchemaCompatibilityError("malformed_metadata", "generated metadata columns are prohibited")
    if _check_constraints(meta[1]) != sorted([
        ("id", "=", "1"),
        ("typeof", "(", "version", ")", "=", "'integer'", "and", "version", ">", "0"),
    ]):
        raise SchemaCompatibilityError("malformed_metadata", "invalid schema_meta CHECK constraints")
    count = conn.execute("SELECT count(*) FROM schema_meta").fetchone()[0]
    if count != 1:
        raise SchemaCompatibilityError("malformed_metadata", "schema_meta must contain exactly one row")
    row = conn.execute(
        "SELECT id, version, created_at, created_by, typeof(id), typeof(version), "
        "typeof(created_at), typeof(created_by) FROM schema_meta"
    ).fetchone()
    identifier, version, created_at, created_by, *types = row
    if types != ["integer", "integer", "text", "text"] or identifier != 1:
        raise SchemaCompatibilityError("malformed_metadata", "invalid ID or metadata storage types")
    if version == 0:
        raise SchemaCompatibilityError("zero_version", "explicit schema version zero is unsupported")
    if version < 0:
        raise SchemaCompatibilityError("malformed_metadata", "schema version must be positive")
    if version != DATABASE_SCHEMA_VERSION:
        raise SchemaCompatibilityError("unsupported_version", f"unsupported schema version {version}")
    expected_columns = [("INTEGER", 0, 1), ("INTEGER", 1, 0), ("TEXT", 1, 0), ("TEXT", 1, 0)]
    if [(col[2].upper(), col[3], col[5]) for col in columns] != expected_columns:
        raise SchemaCompatibilityError("malformed_metadata", "invalid schema_meta column definitions")


def _schema_statements(script: str):
    """Keep trigger bodies intact without executescript's implicit COMMIT."""
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""
    # A trailing comment is harmless; execute also rejects incomplete SQL.
    if statement.strip():
        yield statement


def init_db(db_path: str | Path, create: bool = False) -> sqlite3.Connection:
    """Validate each new connection; initialize only with explicit authorization.

    ADR 0011: no migration, repair, auto-stamping, or identity monitoring.
    Existing databases are opened without SQLite's implicit file creation.
    """
    uri = Path(db_path).resolve().as_uri() + ("?mode=rwc" if create else "?mode=rw")
    conn = sqlite3.connect(uri, uri=True)
    try:
        if create:
            emptiness_sql = (
                "SELECT count(*) FROM sqlite_master "
                "WHERE type IN ('table','index','view','trigger') "
                r"AND name NOT LIKE 'sqlite\_%' ESCAPE '\'"
            )
            if conn.execute(emptiness_sql).fetchone()[0]:
                raise SchemaCompatibilityError("nonempty_database", "fresh initialization requires an empty database")
            # WAL cannot be selected inside a transaction. Do it before creating
            # any schema, so a configuration failure cannot leave committed DDL.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("BEGIN IMMEDIATE")
            # Recheck under the write lock before creating anything.
            if conn.execute(emptiness_sql).fetchone()[0]:
                raise SchemaCompatibilityError("nonempty_database", "fresh initialization requires an empty database")
            for statement in _schema_statements(_SCHEMA_PATH.read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_meta (id, version, created_at, created_by) VALUES (1, ?, ?, ?)",
                (DATABASE_SCHEMA_VERSION, _now_iso(), CREATED_BY),
            )
            _validate_schema(conn)
            conn.commit()
        else:
            # One consistent read transaction for row count and metadata inspection.
            conn.execute("BEGIN")
            _validate_schema(conn)
            conn.commit()
        return conn
    except BaseException:
        conn.rollback()
        conn.close()
        raise


def open_readonly(db_path: str | Path) -> sqlite3.Connection:
    """Open an existing store read-only and run the unchanged schema validator.

    mode=ro protects the database; query_only and the authorizer also refuse
    temporary writes, attachments and attempts to change connection pragmas.
    The caller owns the connection lifetime and any subsequent read transaction.
    """
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.set_authorizer(_readonly_authorizer)
        conn.execute("BEGIN")
        _validate_schema(conn)
        conn.commit()
        return conn
    except BaseException:
        conn.close()
        raise


def _readonly_authorizer(action, arg1, arg2, database, trigger):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                  sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and (
        (arg2 is None and arg1.lower() in ("query_only", "schema_version", "user_version", "database_list"))
        or arg1.lower() in ("table_info", "table_xinfo", "index_info", "index_xinfo", "index_list")
    ):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def read_store_metadata(conn: sqlite3.Connection) -> dict:
    """Stored schema, event count and versions with persisted rows (not registry entries).

    Presence includes append-side indexes and retained materializations, even
    when a version has no published progress yet. No replay or content audit.
    """
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return read_store_metadata(conn)
    tables = [table for table, _ in _RECORD_TABLES.values()]
    tables += ["derived_progress", "identity_event_index", "belief_event_index",
               "committed_roots", "committed_nodes"]
    versions = {row[0] for row in conn.execute(" UNION ".join(
        f"SELECT projector_version FROM {table}" for table in tables))}
    if conn.execute("SELECT EXISTS(SELECT 1 FROM resolved_beliefs) OR "
                    "EXISTS(SELECT 1 FROM entity_event_index)").fetchone()[0]:
        versions.add("0")
    return {"schema_version": conn.execute("SELECT version FROM schema_meta").fetchone()[0],
            "event_count": conn.execute("SELECT count(*) FROM events").fetchone()[0],
            "projector_versions": sorted(versions)}


def read_projection_status(conn: sqlite3.Connection, projector_version: str = "0") -> dict:
    """Disclose stored applied progress against the full log tip, without replay.

    Legacy rows without a checkpoint have unknown freshness. Their timestamps
    and lineage are not substitutes for an applied position (ADR 0014).
    """
    _registered_projector(projector_version)
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return read_projection_status(conn, projector_version)
    row = conn.execute(
        "SELECT d.log_position,d.event_id,e.event_id FROM derived_progress d "
        "LEFT JOIN events e ON e.rowid=d.log_position WHERE d.projector_version=?",
        (projector_version,)).fetchone()
    latest = conn.execute("SELECT rowid,event_id,event_hash FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
    progress = None if row is None else {"projector_version": projector_version,
        "log_position": row[0], "event_id": row[1]}
    freshness = None if latest is None else dict(zip(("log_position", "event_id", "event_hash"), latest))
    if projector_version == "0":
        present = bool(conn.execute("SELECT EXISTS(SELECT 1 FROM resolved_beliefs)").fetchone()[0])
    else:
        tables = [table for table, _ in _RECORD_TABLES.values()] + ["committed_roots"]
        present = any(conn.execute(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE projector_version=?)",
                                  (projector_version,)).fetchone()[0] for table in tables)
    if projector_version == "0" and row is None and present:
        return {"stale": None, "freshness_state": "unknown", "derived_progress": None,
                "append_freshness": freshness, "freshness_scope": "log",
                "reason": "legacy materialization has no recorded applied progress"}
    stale = projection.is_stale(None if row is None else row[0],
        None if latest is None else latest[0], record_present=present or row is not None,
        progress_valid=row is None or row[1] == row[2])
    return {"stale": stale, "freshness_state": "stale" if stale else "fresh",
            "derived_progress": progress, "append_freshness": freshness, "freshness_scope": "log"}


def last_event_hash(conn: sqlite3.Connection) -> str | None:
    """Return the most recently appended event_hash (chain tip), or None if empty.
    Fold/insertion order is rowid (§1)."""
    row = conn.execute("SELECT event_hash FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def safe_append_event(conn: sqlite3.Connection, envelope: Envelope, payload: Payload,
                      projector_version: str = "0") -> bool:
    """Append a validated retained pair and freshness in one transaction.

    Return False only for an identical recorded retry. Reused IDs or idempotency
    keys with different contents refuse; they are not silently ignored.

    Idempotency is enforced by the unique index on idempotency_key. Formerly
    `safe_write_jsonl` under the superseded flat-JSONL design (spec/HANDOFF_2026-07-11.md).
    """
    _registered_projector(projector_version)
    if projector_version in ("1", "2"):
        return _append_stage_two(conn, envelope, payload, projector_version)
    if envelope.event_type not in projection._VALUE_SETTING:
        raise NotImplementedError(f"append handler for {envelope.event_type!r} not implemented")
    if conn.in_transaction:
        raise RuntimeError("append requires its own transaction")
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if _is_recorded_retry(conn, envelope, payload):
            return False
        data = integrity.decode_payload(envelope, payload)
        previous = conn.execute(
            "SELECT event_hash, recorded_at FROM events ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        recorded_at = _instant(envelope.recorded_at, "recorded_at")
        if previous and recorded_at < _instant(previous[1], "recorded_at"):
            raise BackdatedRecordingError(
                f"recorded_at {envelope.recorded_at!r} precedes previous event {previous[1]!r}"
            )
        if envelope.prev_event_hash != (None if previous is None else previous[0]):
            raise integrity.IntegrityError("event was built against a different append position")
        conn.execute(
            f"INSERT INTO events ({','.join(_EVENT_COLUMNS)}) VALUES ({','.join('?' for _ in _EVENT_COLUMNS)})",
            tuple(getattr(envelope, col) for col in _EVENT_COLUMNS))
        # Payloads are keyed by event ID, not content hash (ADR 0007). Conflicting
        # identities have already refused under the same write lock.
        conn.execute(
            "INSERT INTO payloads (event_id, payload_hash, canonical_entity_id, ciphertext, redacted) "
            "VALUES (?,?,?,?,?)",
            (payload.event_id, payload.payload_hash, payload.canonical_entity_id,
             payload.ciphertext, int(payload.redacted)),
        )
        # Synchronous stale-read index, keyed by the belief's entity (§1/§4). For the
        # skeleton the belief_id stands in as the entity key (one belief, no graph yet).
        entity_id = data["belief_id"]
        conn.execute(
            "INSERT INTO entity_event_index (entity_id, latest_event_id, latest_event_hash, updated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(entity_id) DO UPDATE SET "
            "latest_event_id=excluded.latest_event_id, "
            "latest_event_hash=excluded.latest_event_hash, updated_at=excluded.updated_at",
            (entity_id, envelope.event_id, envelope.event_hash, _now_iso()),
        )
    return True


def _recorded_pair(conn, event_id):
    """Read one retained submission and check its actual predecessor association."""
    row = conn.execute(
        f"SELECT e.rowid, e.{',e.'.join(_EVENT_COLUMNS)}, "
        "p.payload_hash,p.event_id,p.canonical_entity_id,p.ciphertext,p.redacted, "
        "(SELECT event_hash FROM events prior WHERE prior.rowid<e.rowid ORDER BY prior.rowid DESC LIMIT 1) "
        "FROM events e LEFT JOIN payloads p ON p.event_id=e.event_id WHERE e.event_id=?",
        (event_id,)).fetchone()
    if row is None:
        return None
    envelope = Envelope(**dict(zip(_EVENT_COLUMNS, row[1:1+len(_EVENT_COLUMNS)])))
    payload = Payload(*row[1+len(_EVENT_COLUMNS):-1])
    integrity.decode_payload(envelope, payload)
    if envelope.prev_event_hash != row[-1]:
        raise integrity.IntegrityError("stored event predecessor mismatch")
    return envelope, payload


def find_recorded_event(conn, idempotency_key):
    """Retrieve a verified retained pair for a legacy raw-submission retry."""
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return find_recorded_event(conn, idempotency_key)
    row = conn.execute("SELECT event_id FROM events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    return None if row is None else _recorded_pair(conn, row[0])


def _is_recorded_retry(conn, envelope, payload):
    rows = conn.execute(
        "SELECT event_id FROM events WHERE event_id=? OR idempotency_key=?",
        (envelope.event_id, envelope.idempotency_key)).fetchall()
    if not rows:
        return False
    if len(rows) != 1 or _recorded_pair(conn, rows[0][0]) != (envelope, payload):
        raise integrity.IntegrityError("retry differs from retained recorded IDs or submitted contents")
    return True


def _append_stage_two(conn, envelope, payload, version="1"):
    """Validate at the locked append prefix; exact retained submissions retry."""
    if envelope.event_type not in SUPPORTED_EVENTS:
        raise NotImplementedError(f"stage two refuses {envelope.event_type!r}")
    if conn.in_transaction:
        raise RuntimeError("append requires its own transaction")
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if _is_recorded_retry(conn, envelope, payload):
            return False
        if payload.redacted or payload.ciphertext is None or payload.canonical_entity_id is not None:
            raise NotImplementedError("stage two does not implement redaction or canonical key binding")
        data = integrity.decode_payload(envelope, payload)
        tip = conn.execute(
            "SELECT rowid,event_id,event_hash,recorded_at FROM events ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if tip and _instant(envelope.recorded_at, "recorded_at") < _instant(tip[3], "recorded_at"):
            raise BackdatedRecordingError("recorded_at precedes previous event")
        snapshot = _read_snapshot(conn, version)
        if (snapshot.log_position, snapshot.event_id) != ((0, None) if tip is None else tip[:2]):
            raise ProjectionBehindError("derived prefix is behind append position; publish pending events first")
        if envelope.prev_event_hash != (None if tip is None else tip[2]):
            raise integrity.IntegrityError("event was built against a different append position")
        delta = projection.PROJECTORS[version].reduce(snapshot, envelope, data, envelope.recorded_at)
        conn.execute(
            f"INSERT INTO events ({','.join(_EVENT_COLUMNS)}) VALUES ({','.join('?' for _ in _EVENT_COLUMNS)})",
            tuple(getattr(envelope, col) for col in _EVENT_COLUMNS),
        )
        conn.execute("INSERT INTO payloads VALUES (?,?,?,?,?)", (
            payload.event_id, payload.payload_hash, payload.canonical_entity_id,
            payload.ciphertext, int(payload.redacted)))
        subjects = set(delta.entities) | {b["subject_id"] for b in delta.beliefs.values()}
        # Both projectors consume this same event contract. Freshness describes
        # Layer A, while progress remains separately pinned to each projector.
        for compatible_version in ("1", "2"):
            for subject_id in subjects:
                conn.execute(
                    "INSERT INTO identity_event_index VALUES (?,?,?) "
                    "ON CONFLICT(projector_version,subject_id) DO UPDATE SET latest_event_id=excluded.latest_event_id",
                    (compatible_version, subject_id, envelope.event_id))
            for belief_id, belief in delta.beliefs.items():
                conn.execute(
                    "INSERT INTO belief_event_index VALUES (?,?,?) "
                    "ON CONFLICT(projector_version,belief_id) DO NOTHING",
                    (compatible_version, belief_id, belief["subject_id"]))
    return True


def read_all_events(conn: sqlite3.Connection) -> list[tuple[Envelope, dict]]:
    """Read and verify the complete Layer A chain, including every payload row.

    Missing or mismatched content refuses. Redaction remains unsupported; no
    absent payload is skipped or represented as usable evidence.
    """
    return [(env, data) for _, env, data in _pending_events(conn, 0)]


def evaluate_whole_view(
    conn: sqlite3.Connection,
    as_of: str,
    projector_version: str = "0",
) -> dict[str, dict]:
    """Evaluate the complete view at an explicit shared time (ADR 0012).

    This opt-in operation reconstructs from one log read. It does not reuse or
    rewrite materialized rows: their cutoff/version cannot be established from
    their timestamps alone. Ordinary read_belief remains a materialized read.
    The selected projector evaluates every included event at as_of, including
    any time-dependent fields; no result is obtained by relabeling cached rows.
    """
    if not isinstance(as_of, str):
        raise ValueError("whole-view evaluation requires an explicit as_of timestamp")
    _instant(as_of, "as_of")
    return projection.project(read_all_events(conn), as_of, projector_version)


def read_belief(conn: sqlite3.Connection, belief_id: str,
                projector_version: str = "0") -> dict | None:
    """Read one materialized belief, or None; versions 1 and 2 include a stale label.

    read_belief_status exposes progress/freshness separately, including when no
    belief has been materialized yet. Version 0 retains its original return shape.
    """
    _registered_projector(projector_version)
    if projector_version in ("1", "2"):
        # Row and freshness come from one consistent SQLite read snapshot. Stale
        # metadata is operational disclosure, not part of the projected content.
        status = read_belief_status(conn, belief_id, projector_version)
        belief = status["belief"]
        return None if belief is None else {**belief, "stale": status["stale"]}
    row = conn.execute(
        "SELECT belief_id, current_value, value_occurred_at, verification_state, "
        "verifiability, display_origin, supporting_events, opposing_events, "
        "superseding_events, resolution_basis, view_version_hash, projected_as_of, updated_at "
        "FROM resolved_beliefs WHERE belief_id = ?",
        (belief_id,),
    ).fetchone()
    if row is None:
        return None
    belief = {
        "belief_id": row[0], "current_value": row[1], "value_occurred_at": row[2],
        "verification_state": row[3], "verifiability": row[4], "display_origin": row[5],
        "supporting_events": json.loads(row[6]), "opposing_events": json.loads(row[7]),
        "superseding_events": json.loads(row[8]), "resolution_basis": row[9],
        "view_version_hash": row[10], "projected_as_of": row[11], "updated_at": row[12],
    }
    return belief


def upsert_belief(conn: sqlite3.Connection, belief: dict) -> None:
    """Materialize a folded belief into resolved_beliefs (a reconstructible
    derivative — Invariant 8; always rebuildable from Layer A via full replay)."""
    with conn:
        _upsert_legacy_belief(conn, belief)


def _upsert_legacy_belief(conn: sqlite3.Connection, belief: dict) -> None:
    """Original row serialization, within the caller's transaction."""
    conn.execute(
            "INSERT INTO resolved_beliefs (belief_id, current_value, value_occurred_at, "
            "verification_state, verifiability, display_origin, supporting_events, "
            "opposing_events, superseding_events, resolution_basis, view_version_hash, "
            "projected_as_of, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(belief_id) DO UPDATE SET "
            "current_value=excluded.current_value, value_occurred_at=excluded.value_occurred_at, "
            "verification_state=excluded.verification_state, verifiability=excluded.verifiability, "
            "display_origin=excluded.display_origin, supporting_events=excluded.supporting_events, "
            "opposing_events=excluded.opposing_events, "
            "superseding_events=excluded.superseding_events, "
            "resolution_basis=excluded.resolution_basis, "
            "view_version_hash=excluded.view_version_hash, projected_as_of=excluded.projected_as_of, "
            "updated_at=excluded.updated_at",
            (belief["belief_id"], belief["current_value"], belief["value_occurred_at"],
             belief["verification_state"], belief["verifiability"], belief["display_origin"],
             json.dumps(belief["supporting_events"]), json.dumps(belief["opposing_events"]),
             json.dumps(belief["superseding_events"]), belief["resolution_basis"],
             belief["view_version_hash"], belief["projected_as_of"], belief["updated_at"]),
        )


class ProjectionBehindError(RuntimeError):
    """Acceptance requires materialization at the actual pre-append prefix."""


def _registered_projector(version: str):
    if not isinstance(version, str) or version not in projection.PROJECTORS:
        raise ValueError(f"Unsupported projector_version: {version!r}")
    return projection.PROJECTORS[version]


def _snapshot_projector(version: str):
    projector = _registered_projector(version)
    if not isinstance(projector, projection.ReducerProjector):
        raise ValueError(f"Projector {version!r} does not use the snapshot boundary")
    return projector


_RECORD_TABLES = {
    "beliefs": ("projected_beliefs", "belief_id"),
    "entities": ("projected_entities", "subject_id"),
    "mentions": ("projected_mentions", "mention_id"),
    "entity_links": ("projected_entity_links", "mention_id"),
    "claim_candidates": ("projected_claim_candidates", "claim_candidate_id"),
    "events": ("projected_events", "event_id"),
}


def _read_snapshot(conn: sqlite3.Connection, version: str) -> projection.Snapshot:
    """Caller owns one transaction across these reads and publication/acceptance."""
    if not conn.in_transaction:
        raise RuntimeError("snapshot reads require a transaction")
    if version == "2":
        return committed_storage.read_snapshot(conn)
    progress = conn.execute(
        "SELECT log_position, event_id FROM derived_progress WHERE projector_version = ?",
        (version,),
    ).fetchone()
    records = {}
    if version == "0":
        beliefs = {key: read_belief(conn, key) for (key,) in conn.execute(
            "SELECT belief_id FROM resolved_beliefs"
        ).fetchall()}
    else:
        for kind, (table, column) in _RECORD_TABLES.items():
            records[kind] = {key: json.loads(content) for key, content in conn.execute(
                f"SELECT {column}, content FROM {table} WHERE projector_version = ?", (version,))}
        beliefs = records.pop("beliefs")
    if progress is None:
        if beliefs or any(records.values()):
            raise RuntimeError("unproven derived rows; recover by full replay")
        return projection.Snapshot({}, projector_version=version)
    applied = conn.execute("SELECT event_id FROM events WHERE rowid = ?", (progress[0],)).fetchone()
    if applied != (progress[1],):
        raise RuntimeError("derived progress does not identify a log prefix; recover by full replay")
    return projection.Snapshot(beliefs, *progress, projector_version=version, **records)


def read_snapshot(conn, projector_version="1"):
    """Read all derived records and progress in one consistent transaction."""
    _snapshot_projector(projector_version)
    if conn.in_transaction:
        snapshot = _read_snapshot(conn, projector_version)
        return snapshot.detached() if projector_version == "2" else snapshot
    with conn:
        conn.execute("BEGIN")
        snapshot = _read_snapshot(conn, projector_version)
        return snapshot.detached() if projector_version == "2" else snapshot


def _read_record(conn, kind, identifier, projector_version="1"):
    _snapshot_projector(projector_version)
    if projector_version == "2":
        if conn.in_transaction:
            return _read_snapshot(conn, "2").record(kind, identifier)
        with conn:
            conn.execute("BEGIN")
            return _read_snapshot(conn, "2").record(kind, identifier)
    table, column = _RECORD_TABLES[kind]
    row = conn.execute(f"SELECT content FROM {table} WHERE projector_version=? AND {column}=?",
                       (projector_version, identifier)).fetchone()
    return None if row is None else json.loads(row[0])


class StaleProjectionWarning(UserWarning):
    """A raw identity lookup used an incomplete publication; status is attached."""

    def __init__(self, status):
        self.status = status
        super().__init__("identity projection is stale; absence is not authoritative; "
                         "inspect read_identity_status for progress and append freshness")


def read_identity_status(conn, kind, identifier, projector_version="1"):
    """Read identity content and freshness together without replaying pending events.

    For an absent mention/link its subject is not known from materialization, so
    conservatively disclose whole-log lag. Once caught up, absence is conclusive.
    Existing records and entity IDs use the append-side subject index.
    """
    _snapshot_projector(projector_version)
    if kind not in ("entities", "mentions", "entity_links"):
        raise ValueError("identity status requires an entity, mention, or entity link")
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return read_identity_status(conn, kind, identifier, projector_version)
    record = _read_record(conn, kind, identifier, projector_version)
    progress_row = conn.execute(
        "SELECT d.log_position,d.event_id,e.event_id FROM derived_progress d "
        "LEFT JOIN events e ON e.rowid=d.log_position WHERE d.projector_version=?",
        (projector_version,)).fetchone()
    position = None if progress_row is None else progress_row[0]
    progress = None if progress_row is None else {
        "projector_version": projector_version, "log_position": position, "event_id": progress_row[1]}
    subject = identifier if kind == "entities" else (None if record is None else record["subject_id"])
    if subject is None:
        scope = "log"
        latest = conn.execute("SELECT rowid,event_id,event_hash FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
    else:
        scope = "subject"
        latest = conn.execute(
            "SELECT e.rowid,e.event_id,e.event_hash FROM identity_event_index i "
            "JOIN events e ON e.event_id=i.latest_event_id WHERE i.projector_version=? AND i.subject_id=?",
            (projector_version, subject)).fetchone()
    freshness = None if latest is None else {
        "log_position": latest[0], "event_id": latest[1], "event_hash": latest[2]}
    # With no known subject, a missing record does not itself prove staleness:
    # the whole-log position establishes whether this absence is authoritative.
    present = record is not None or (scope == "log" and position is not None)
    stale = projection.is_stale(position, None if latest is None else latest[0],
                                record_present=present,
                                progress_valid=progress_row is None or progress_row[1] == progress_row[2])
    return {"record": record, "stale": stale, "derived_progress": progress,
            "append_freshness": freshness, "freshness_scope": scope}


def read_entity_status(conn, subject_id, projector_version="1"):
    return read_identity_status(conn, "entities", subject_id, projector_version)


def read_mention_status(conn, mention_id, projector_version="1"):
    return read_identity_status(conn, "mentions", mention_id, projector_version)


def read_entity_link_status(conn, mention_id, projector_version="1"):
    return read_identity_status(conn, "entity_links", mention_id, projector_version)


def _read_identity(conn, kind, identifier, version):
    status = read_identity_status(conn, kind, identifier, version)
    if status["stale"]:
        warnings.warn(StaleProjectionWarning(status), stacklevel=3)
    return status["record"]


def read_entity(conn, subject_id, projector_version="1"):
    return _read_identity(conn, "entities", subject_id, projector_version)


def read_mention(conn, mention_id, projector_version="1"):
    return _read_identity(conn, "mentions", mention_id, projector_version)


def read_entity_link(conn, mention_id, projector_version="1"):
    return _read_identity(conn, "entity_links", mention_id, projector_version)


def read_claim_candidate(conn, claim_candidate_id, projector_version="1"):
    return _read_record(conn, "claim_candidates", claim_candidate_id, projector_version)


def read_claim_candidate_value(conn, claim_candidate_id, projector_version="1"):
    candidate = read_claim_candidate(conn, claim_candidate_id, projector_version)
    if candidate is None:
        raise KeyError(f"unknown ClaimCandidate: {claim_candidate_id!r}")
    return candidate["value"]


def read_belief_scalar(conn, belief_id, projector_version="1"):
    from .reducer import scalar_belief_value
    belief = read_belief(conn, belief_id, projector_version)
    if belief is None:
        raise KeyError(f"unknown belief: {belief_id!r}")
    return scalar_belief_value(belief)


def lookup_current_belief_id(conn, subject_id, property_id, projector_version="1"):
    """Writer lookup uses the recorded pair, with exact string equality."""
    _snapshot_projector(projector_version)
    row = conn.execute(
        "SELECT belief_id FROM projected_beliefs WHERE projector_version=? "
        "AND json_extract(content,'$.subject_id')=? AND json_extract(content,'$.property_id')=? "
        "AND json_extract(content,'$.lifecycle_status')='current'",
        (projector_version, subject_id, property_id)).fetchone()
    return None if row is None else row[0]


def _publish_delta(conn: sqlite3.Connection, version: str, position: int, delta) -> None:
    """Persist the complete reducer result; never complete semantics in storage.

    Deliberately no connection context/commit here: all rows and progress belong
    to the caller's single publication transaction.
    """
    if not conn.in_transaction:
        raise RuntimeError("delta publication requires a transaction")
    if version == "2":
        committed_storage.publish(conn, delta)
    for key, belief in ({} if version == "2" else delta.beliefs).items():
        if version == "0":
            _upsert_legacy_belief(conn, belief)
        else:
            conn.execute(
                "INSERT INTO projected_beliefs (projector_version, belief_id, content) VALUES (?, ?, ?) "
                "ON CONFLICT(projector_version, belief_id) DO UPDATE SET content=excluded.content",
                (version, key, hashing.canonical_json(belief)),
            )
    if version not in ("0", "2"):
        for kind in RECORD_KINDS:
            if kind == "beliefs":
                continue
            table, column = _RECORD_TABLES[kind]
            for key, record in getattr(delta, kind).items():
                if kind == "entity_links":
                    conn.execute(
                        "INSERT INTO projected_entity_links VALUES (?,?,?,?,?) "
                        "ON CONFLICT(projector_version,mention_id) DO UPDATE SET "
                        "content=excluded.content,link_state=excluded.link_state,"
                        "entity_link_confidence=excluded.entity_link_confidence",
                        (version, key, hashing.canonical_json(record), record["link_state"],
                         record["entity_link_confidence"]))
                else:
                    conn.execute(
                        f"INSERT INTO {table} VALUES (?,?,?) ON CONFLICT(projector_version,{column}) "
                        "DO UPDATE SET content=excluded.content",
                        (version, key, hashing.canonical_json(record)))
    conn.execute(
        "INSERT INTO derived_progress (projector_version, log_position, event_id) VALUES (?, ?, ?) "
        "ON CONFLICT(projector_version) DO UPDATE SET "
        "log_position=excluded.log_position, event_id=excluded.event_id",
        (version, position, delta.event_id),
    )


def _pending_events(conn: sqlite3.Connection, position: int, *, limit: int = -1):
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return _pending_events(conn, position, limit=limit)
    previous_hash, previous_recorded_at = None, None
    if position:
        anchor = conn.execute(
            f"SELECT {','.join(_EVENT_COLUMNS)} FROM events WHERE rowid=?", (position,)).fetchone()
        if anchor is None:
            raise integrity.IntegrityError("missing event at derived progress")
        envelope, _ = _recorded_pair(conn, anchor[0])
        previous_hash = envelope.event_hash
        previous_recorded_at = _instant(envelope.recorded_at, "recorded_at")
    rows = conn.execute(
        f"SELECT e.rowid, e.{', e.'.join(_EVENT_COLUMNS)}, "
        "p.payload_hash,p.event_id,p.canonical_entity_id,p.ciphertext,p.redacted "
        "FROM events e LEFT JOIN payloads p ON p.event_id = e.event_id "
        "WHERE e.rowid > ? ORDER BY e.rowid LIMIT ?", (position, limit),
    ).fetchall()
    entries = []
    for row in rows:
        envelope = Envelope(**dict(zip(_EVENT_COLUMNS, row[1:1+len(_EVENT_COLUMNS)])))
        payload = Payload(*row[1+len(_EVENT_COLUMNS):])
        entries.append((envelope, integrity.decode_payload(envelope, payload)))
    verified = integrity.verified_log(entries, previous_hash, previous_recorded_at)
    return [(row[0], envelope, data) for row, (envelope, data) in zip(rows, verified)]


def materialize_pending(conn: sqlite3.Connection, as_of: str,
                        projector_version: str = "1") -> int:
    """Worker path: publish each next complete event once, in log order.

    Append has already committed in a separate transaction. A retry after worker
    acknowledgement loss starts after published progress. Crash recovery uses
    rebuild_projection(), never a possibly partial snapshot.
    """
    projector = _registered_projector(projector_version)
    cutoff = _instant(as_of, "as_of")
    if conn.in_transaction:
        raise RuntimeError("derived publication requires its own transaction")
    applied = 0
    while True:
        with conn:
            conn.execute("BEGIN IMMEDIATE")
            snapshot = _read_snapshot(conn, projector_version)
            pending = _pending_events(conn, snapshot.log_position, limit=1)
            if not pending or _instant(pending[0][1].recorded_at, "recorded_at") > cutoff:
                return applied
            position, envelope, payload = pending[0]
            if isinstance(projector, projection.ReducerProjector):
                delta = projector.reduce(snapshot, envelope, payload, as_of)
            else:
                # Keep the registered legacy fold and its serialization intact.
                # Progress lets version 0 catch up after writes under version 1.
                if envelope.event_type not in projection._VALUE_SETTING:
                    raise NotImplementedError(f"fold handler for {envelope.event_type!r} not implemented")
                key = payload["belief_id"]
                delta = EventDelta(envelope.event_id, {
                    key: projector(snapshot.belief(key), envelope, payload, as_of),
                })
            _publish_delta(conn, projector_version, position, delta)
        applied += 1


def rebuild_projection(conn: sqlite3.Connection, as_of: str,
                       projector_version: str = "1") -> dict[str, dict]:
    """Recovery: full replay from Layer A, atomically replace this version's view.

    No reads of derived rows or progress authorize reconstruction. On any failure
    the previous publication remains committed and available with stale labels.
    """
    projector = _snapshot_projector(projector_version)
    cutoff = _instant(as_of, "as_of")
    if conn.in_transaction:
        raise RuntimeError("recovery requires its own transaction")
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        log = _pending_events(conn, 0)
        for table, _ in _RECORD_TABLES.values():
            conn.execute(f"DELETE FROM {table} WHERE projector_version = ?", (projector_version,))
        if projector_version == "2":
            conn.execute("DELETE FROM committed_roots WHERE projector_version='2'")
            conn.execute("DELETE FROM committed_nodes WHERE projector_version='2'")
        conn.execute("DELETE FROM derived_progress WHERE projector_version = ?", (projector_version,))
        snapshot = (committed.Snapshot() if projector_version == "2"
                    else projection.Snapshot({}, projector_version=projector_version))
        for next_position, envelope, payload in log:
            if _instant(envelope.recorded_at, "recorded_at") > cutoff:
                break
            delta = projector.reduce(snapshot, envelope, payload, as_of)
            snapshot = snapshot.apply(delta, next_position)
            _publish_delta(conn, projector_version, next_position, delta)
    return snapshot.beliefs()


def read_belief_status(conn: sqlite3.Connection, belief_id: str,
                       projector_version: str = "1") -> dict:
    """One consistent materialized read with append freshness and derived progress.

    No reconstruction or digest comparison. The append-side belief association
    also locates a subject before the first belief has been materialized.
    Version 0 uses its legacy append index and recorded publication checkpoint;
    a legacy record without that checkpoint returns stale=None (unknown).
    """
    if projector_version == "0":
        return _read_legacy_belief_status(conn, belief_id)
    _snapshot_projector(projector_version)
    if projector_version == "2" and not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return read_belief_status(conn, belief_id, projector_version)
    row = conn.execute(
        "SELECT b.content, d.log_position, d.event_id, e.rowid, e.event_id, "
        "e.event_hash, applied.event_id "
        "FROM (SELECT ? AS belief_id, ? AS projector_version) AS request "
        "LEFT JOIN projected_beliefs b ON b.belief_id=request.belief_id "
        "AND b.projector_version=request.projector_version "
        "LEFT JOIN derived_progress d ON d.projector_version=request.projector_version "
        "LEFT JOIN belief_event_index bi ON bi.belief_id=request.belief_id "
        "AND bi.projector_version=request.projector_version "
        "LEFT JOIN identity_event_index i ON i.subject_id=COALESCE("
        "json_extract(b.content,'$.subject_id'),bi.subject_id) "
        "AND i.projector_version=request.projector_version "
        "LEFT JOIN events e ON e.event_id=i.latest_event_id "
        "LEFT JOIN events applied ON applied.rowid=d.log_position",
        (belief_id, projector_version),
    ).fetchone()
    content, position, event_id, latest_position, latest_id, latest_hash, applied_id = row
    progress = None if position is None else {"projector_version": projector_version,
                                            "log_position": position, "event_id": event_id}
    freshness = None if latest_position is None else {
        "log_position": latest_position, "event_id": latest_id, "event_hash": latest_hash,
    }
    stale = projection.is_stale(position, latest_position, record_present=content is not None,
                                progress_valid=position is None or event_id == applied_id)
    belief = None if content is None else json.loads(content)
    if projector_version == "2" and belief is not None:
        snapshot = _read_snapshot(conn, "2")
        if snapshot.header(belief_id) != belief:
            raise ValueError("belief lookup header differs from committed record")
        belief = snapshot.belief(belief_id)
    return {"belief": belief, "stale": stale,
            "derived_progress": progress, "append_freshness": freshness}


def _read_legacy_belief_status(conn, belief_id):
    if not conn.in_transaction:
        with conn:
            conn.execute("BEGIN")
            return _read_legacy_belief_status(conn, belief_id)
    belief = read_belief(conn, belief_id, "0")
    status = read_projection_status(conn, "0")
    latest = conn.execute(
        "SELECT e.rowid,e.event_id,e.event_hash FROM entity_event_index i "
        "JOIN events e ON e.event_id=i.latest_event_id WHERE i.entity_id=?", (belief_id,)).fetchone()
    freshness = None if latest is None else dict(zip(("log_position", "event_id", "event_hash"), latest))
    progress = status["derived_progress"]
    if belief is not None and progress is None:
        stale = None
    else:
        stale = projection.is_stale(None if progress is None else progress["log_position"],
            None if latest is None else latest[0], record_present=belief is not None,
            progress_valid=progress is None or conn.execute(
                "SELECT event_id FROM events WHERE rowid=?", (progress["log_position"],)
            ).fetchone() == (progress["event_id"],))
    result = {"belief": belief, "stale": stale, "derived_progress": progress,
              "append_freshness": freshness,
              "freshness_state": "unknown" if stale is None else ("stale" if stale else "fresh")}
    if stale is None:
        result["reason"] = "legacy materialization has no recorded applied progress"
    return result
