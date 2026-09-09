"""Layer A storage — the append-only Reality Layer, and derived-table access.

spec/NYX_ARCHITECTURE.md §1 (substrate, write path) and
spec/NYX_V0_IMPLEMENTATION.md §4 (schema). The append is THE durable commit
(Invariant 8) — everything else is a reconstructible derivative.

Append-only is engine-enforced (UPDATE/DELETE triggers in schema.sql), not a
convention (Invariant 1). `safe_append_event` is the sole write path into Layer A;
it inserts the envelope + payload AND updates `entity_event_index` synchronously in
ONE transaction (the one exception to "append is the only sync step" — §1; without
it, stale-read detection races the async projection).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import hashing, projection
from .events import Envelope, Payload
from .projection import _instant
from .reducer import EventDelta

# schema.sql lives at the repo root: src/nyx/storage.py -> parents[2].
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"

_EVENT_COLUMNS = (
    "event_id", "idempotency_key", "schema_version", "event_type",
    "occurred_at", "recorded_at", "source", "source_class", "origin_type",
    "payload_hash", "entity_refs", "prev_event_hash", "event_hash",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DATABASE_SCHEMA_VERSION = 2  # ADR 0016; version-1 databases refuse unchanged.
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


def last_event_hash(conn: sqlite3.Connection) -> str | None:
    """Return the most recently appended event_hash (chain tip), or None if empty.
    Fold/insertion order is rowid (§1)."""
    row = conn.execute("SELECT event_hash FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def safe_append_event(conn: sqlite3.Connection, envelope: Envelope, payload: Payload,
                      projector_version: str = "0") -> bool:
    """Append one event to Layer A: envelope + payload + entity_event_index, all in
    a single transaction (Invariant 8, §1). Returns True if newly appended, False if
    the idempotency key already existed (dedup — no second row).

    Idempotency is enforced by the unique index on idempotency_key. Formerly
    `safe_write_jsonl` under the superseded flat-JSONL design (spec/HANDOFF_2026-07-11.md).
    """
    _registered_projector(projector_version)
    if envelope.event_type not in projection._VALUE_SETTING:
        raise NotImplementedError(f"append handler for {envelope.event_type!r} not implemented")
    with conn:  # atomic transaction
        cur = conn.execute(
            f"INSERT OR IGNORE INTO events ({','.join(_EVENT_COLUMNS)}) "
            f"VALUES ({','.join('?' for _ in _EVENT_COLUMNS)})",
            tuple(getattr(envelope, col) for col in _EVENT_COLUMNS),
        )
        if cur.rowcount == 0:
            return False  # duplicate idempotency_key — no-op, no second row
        # The tentative insert acquires the write lock. A refusal rolls it back
        # before payload/index writes; duplicates remain idempotent no-ops.
        previous = conn.execute(
            "SELECT recorded_at FROM events WHERE rowid < ? ORDER BY rowid DESC LIMIT 1",
            (cur.lastrowid,),
        ).fetchone()
        recorded_at = _instant(envelope.recorded_at, "recorded_at")
        if previous and recorded_at < _instant(previous[0], "recorded_at"):
            raise BackdatedRecordingError(
                f"recorded_at {envelope.recorded_at!r} precedes previous event {previous[0]!r}"
            )
        if projector_version == "1":
            # The tentative insert owns the write lock. Validate against the
            # actual append prefix, not a head read before a concurrent append.
            tip = conn.execute(
                "SELECT rowid, event_id, event_hash FROM events WHERE rowid < ? "
                "ORDER BY rowid DESC LIMIT 1", (cur.lastrowid,),
            ).fetchone()
            snapshot = _read_snapshot(conn, projector_version)
            expected = (0, None) if tip is None else tip[:2]
            if (snapshot.log_position, snapshot.event_id) != expected:
                raise ProjectionBehindError("derived prefix is behind append position; publish pending events first")
            if envelope.prev_event_hash != (None if tip is None else tip[2]):
                raise ValueError("event was built against a different append position")
            projection.PROJECTORS[projector_version].reduce(
                snapshot, envelope, json.loads(payload.ciphertext), envelope.recorded_at,
            )
        # Keyed by event_id (decisions/0007). No conflict clause, deliberately: the
        # events INSERT OR IGNORE above already returned False on a duplicate
        # idempotency_key, so this line is reached ONLY for a freshly-appended event —
        # whose event_id is new by construction. A PK violation here would therefore be
        # a real bug (a reused event_id), and must fail loudly rather than be absorbed
        # by an ON CONFLICT. Note payload_hash is deliberately NOT unique: two
        # independent sources reporting the same value share a content hash, and that
        # is corroboration, not duplication.
        conn.execute(
            "INSERT INTO payloads (event_id, payload_hash, canonical_entity_id, ciphertext, redacted) "
            "VALUES (?,?,?,?,?)",
            (payload.event_id, payload.payload_hash, payload.canonical_entity_id,
             payload.ciphertext, int(payload.redacted)),
        )
        # Synchronous stale-read index, keyed by the belief's entity (§1/§4). For the
        # skeleton the belief_id stands in as the entity key (one belief, no graph yet).
        entity_id = json.loads(payload.ciphertext)["belief_id"]
        conn.execute(
            "INSERT INTO entity_event_index (entity_id, latest_event_id, latest_event_hash, updated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(entity_id) DO UPDATE SET "
            "latest_event_id=excluded.latest_event_id, "
            "latest_event_hash=excluded.latest_event_hash, updated_at=excluded.updated_at",
            (entity_id, envelope.event_id, envelope.event_hash, _now_iso()),
        )
    return True


def read_all_events(conn: sqlite3.Connection) -> list[tuple[Envelope, dict]]:
    """Read the full log in insertion (rowid) order as (Envelope, payload_dict)
    pairs — the input to a full replay (spec §6, projection.project). A redacted
    payload (ciphertext NULL) yields a None payload (typed REDACTED sentinel is a
    later slice; the skeleton has no redactions)."""
    rows = conn.execute(
        f"SELECT e.{', e.'.join(_EVENT_COLUMNS)}, p.ciphertext "
        "FROM events e JOIN payloads p ON p.event_id = e.event_id ORDER BY e.rowid"
    ).fetchall()
    out: list[tuple[Envelope, dict]] = []
    for row in rows:
        env = Envelope(**dict(zip(_EVENT_COLUMNS, row[:-1])))
        payload_dict = json.loads(row[-1]) if row[-1] is not None else None
        out.append((env, payload_dict))
    return out


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
    """Read one materialized belief, or None; version 1 includes a stale label.

    read_belief_status exposes progress/freshness separately, including when no
    belief has been materialized yet. Version 0 retains its original return shape.
    """
    _registered_projector(projector_version)
    if projector_version == "1":
        # Row and freshness come from one SQLite statement/read snapshot. Stale
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


def _read_snapshot(conn: sqlite3.Connection, version: str) -> projection.Snapshot:
    """Caller owns one transaction across these reads and publication/acceptance."""
    if not conn.in_transaction:
        raise RuntimeError("snapshot reads require a transaction")
    progress = conn.execute(
        "SELECT log_position, event_id FROM derived_progress WHERE projector_version = ?",
        (version,),
    ).fetchone()
    if version == "0":
        beliefs = {key: read_belief(conn, key) for (key,) in conn.execute(
            "SELECT belief_id FROM resolved_beliefs"
        ).fetchall()}
    else:
        beliefs = {key: json.loads(content) for key, content in conn.execute(
            "SELECT belief_id, content FROM projected_beliefs WHERE projector_version = ?",
            (version,),
        )}
    if progress is None:
        if beliefs:
            raise RuntimeError("unproven derived rows; recover by full replay")
        return projection.Snapshot({}, projector_version=version)
    applied = conn.execute("SELECT event_id FROM events WHERE rowid = ?", (progress[0],)).fetchone()
    if applied != (progress[1],):
        raise RuntimeError("derived progress does not identify a log prefix; recover by full replay")
    return projection.Snapshot(beliefs, *progress, projector_version=version)


def _publish_delta(conn: sqlite3.Connection, version: str, position: int, delta) -> None:
    """Persist the complete reducer result; never complete semantics in storage.

    Deliberately no connection context/commit here: all rows and progress belong
    to the caller's single publication transaction.
    """
    if not conn.in_transaction:
        raise RuntimeError("delta publication requires a transaction")
    for key, belief in delta.beliefs.items():
        if version == "0":
            _upsert_legacy_belief(conn, belief)
        else:
            conn.execute(
                "INSERT INTO projected_beliefs (projector_version, belief_id, content) VALUES (?, ?, ?) "
                "ON CONFLICT(projector_version, belief_id) DO UPDATE SET content=excluded.content",
                (version, key, hashing.canonical_json(belief)),
            )
    conn.execute(
        "INSERT INTO derived_progress (projector_version, log_position, event_id) VALUES (?, ?, ?) "
        "ON CONFLICT(projector_version) DO UPDATE SET "
        "log_position=excluded.log_position, event_id=excluded.event_id",
        (version, position, delta.event_id),
    )


def _pending_events(conn: sqlite3.Connection, position: int, *, limit: int = -1):
    rows = conn.execute(
        f"SELECT e.rowid, e.{', e.'.join(_EVENT_COLUMNS)}, p.ciphertext "
        "FROM events e JOIN payloads p ON p.event_id = e.event_id "
        "WHERE e.rowid > ? ORDER BY e.rowid LIMIT ?", (position, limit),
    ).fetchall()
    return [(row[0], Envelope(**dict(zip(_EVENT_COLUMNS, row[1:-1]))),
             json.loads(row[-1]) if row[-1] is not None else None) for row in rows]


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
        conn.execute("DELETE FROM projected_beliefs WHERE projector_version = ?", (projector_version,))
        conn.execute("DELETE FROM derived_progress WHERE projector_version = ?", (projector_version,))
        beliefs = {}
        position, event_id = 0, None
        for next_position, envelope, payload in log:
            if _instant(envelope.recorded_at, "recorded_at") > cutoff:
                break
            snapshot = projection.Snapshot(beliefs, position, event_id, projector_version)
            delta = projector.reduce(snapshot, envelope, payload, as_of)
            beliefs.update(delta.beliefs)
            _publish_delta(conn, projector_version, next_position, delta)
            position, event_id = next_position, envelope.event_id
    return beliefs


def read_belief_status(conn: sqlite3.Connection, belief_id: str,
                       projector_version: str = "1") -> dict:
    """One consistent materialized read with append freshness and derived progress.

    No reconstruction or digest comparison. Ordinary stage-one events use the
    skeleton's belief-scoped append index; identity coverage is a later stage.
    """
    _snapshot_projector(projector_version)
    row = conn.execute(
        "SELECT b.content, d.log_position, d.event_id, e.rowid, e.event_id, "
        "e.event_hash, applied.event_id "
        "FROM (SELECT ? AS belief_id, ? AS projector_version) AS request "
        "LEFT JOIN projected_beliefs b ON b.belief_id=request.belief_id "
        "AND b.projector_version=request.projector_version "
        "LEFT JOIN derived_progress d ON d.projector_version=request.projector_version "
        "LEFT JOIN entity_event_index i ON i.entity_id=request.belief_id "
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
    stale = ((position is not None and event_id != applied_id)
             or (content is not None and position is None)
             or (latest_position is not None and
                 (content is None or latest_position > (position or 0))))
    return {"belief": None if content is None else json.loads(content), "stale": stale,
            "derived_progress": progress, "append_freshness": freshness}
