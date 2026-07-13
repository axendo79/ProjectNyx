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
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .events import Envelope, Payload

# schema.sql lives at the repo root: src/nyx/storage.py -> parents[2].
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema.sql"

_EVENT_COLUMNS = (
    "event_id", "idempotency_key", "schema_version", "event_type",
    "occurred_at", "recorded_at", "source", "source_class", "origin_type",
    "payload_hash", "entity_refs", "prev_event_hash", "event_hash",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Open the database, applying schema.sql exactly once (WAL, append-only
    triggers). Idempotent: safe to call on an already-initialised database.
    spec/NYX_V0_IMPLEMENTATION.md §4.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    already = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
    ).fetchone()
    if not already:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    return conn


def last_event_hash(conn: sqlite3.Connection) -> str | None:
    """Return the most recently appended event_hash (chain tip), or None if empty.
    Fold/insertion order is rowid (§1)."""
    row = conn.execute("SELECT event_hash FROM events ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def safe_append_event(conn: sqlite3.Connection, envelope: Envelope, payload: Payload) -> bool:
    """Append one event to Layer A: envelope + payload + entity_event_index, all in
    a single transaction (Invariant 8, §1). Returns True if newly appended, False if
    the idempotency key already existed (dedup — no second row).

    Idempotency is enforced by the unique index on idempotency_key. Formerly
    `safe_write_jsonl` under the superseded flat-JSONL design (spec/HANDOFF_2026-07-11.md).
    """
    with conn:  # atomic transaction
        cur = conn.execute(
            f"INSERT OR IGNORE INTO events ({','.join(_EVENT_COLUMNS)}) "
            f"VALUES ({','.join('?' for _ in _EVENT_COLUMNS)})",
            tuple(getattr(envelope, col) for col in _EVENT_COLUMNS),
        )
        if cur.rowcount == 0:
            return False  # duplicate idempotency_key — no-op, no second row
        conn.execute(
            "INSERT INTO payloads (payload_hash, event_id, canonical_entity_id, ciphertext, redacted) "
            "VALUES (?,?,?,?,?)",
            (payload.payload_hash, payload.event_id, payload.canonical_entity_id,
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


def read_belief(conn: sqlite3.Connection, belief_id: str) -> dict | None:
    """Read one materialized belief from resolved_beliefs, or None."""
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
