"""Layer A storage — the append-only Reality Layer, and derived-table access.

spec/NYX_ARCHITECTURE.md §1 (substrate, write path) and
spec/NYX_V0_IMPLEMENTATION.md §4 (schema). The append is THE durable commit
(Invariant 8) — everything else is a reconstructible derivative.

Append-only is engine-enforced (UPDATE/DELETE triggers in schema.sql), not a
convention (Invariant 1). `safe_append_event` is the sole write path into Layer A;
it must, in ONE transaction, insert the envelope + payload AND update
`entity_event_index` synchronously (the one exception to "append is the only sync
step" — §1; without it, stale-read detection races the async projection).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .events import Envelope, Payload


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Create/open the database and apply schema.sql (WAL mode, append-only
    triggers). spec/NYX_V0_IMPLEMENTATION.md §4. Implement in the walking skeleton.
    """
    raise NotImplementedError(
        "init_db — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §4, §6"
    )


def safe_append_event(conn: sqlite3.Connection, envelope: Envelope, payload: Payload) -> None:
    """Append one event to Layer A: insert envelope + payload and update
    entity_event_index, atomically in a single transaction (Invariant 8, §1).

    Idempotency is enforced by the unique index on idempotency_key: re-appending
    the same event must NOT create a second row (walking-skeleton acceptance bar,
    spec/NYX_V0_IMPLEMENTATION.md §6). Formerly `safe_write_jsonl` under the
    superseded flat-JSONL design — see spec/HANDOFF_2026-07-11.md.
    """
    raise NotImplementedError(
        "safe_append_event — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §6, spec/NYX_ARCHITECTURE.md §1"
    )


def read_all_events(conn: sqlite3.Connection) -> list[Envelope]:
    """Read the full event log in insertion (rowid) order — the input to a full
    replay (spec/NYX_V0_IMPLEMENTATION.md §6, projection.project). Implement in
    the walking skeleton.
    """
    raise NotImplementedError(
        "read_all_events — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §6"
    )
