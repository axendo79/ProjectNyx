"""Content-addressing and tamper-evidence hashing — the single canonical utility.

spec/NYX_V0_IMPLEMENTATION.md §1. Everything hashable in Nyx goes through here so
there is exactly one canonicalization discipline (sorted keys, fixed float format,
no whitespace variance). The Liver's dependency hash (§3) and the process trace's
hypothesis/semantic hash (§7) are the SAME underlying pattern and MUST share this
utility — do not grow a second ad hoc scheme (spec §13 unification TBD, closed here).

Hash determinism is load-bearing: `event_hash` and `view_version_hash` must be
byte-for-byte reproducible across machines (see .gitattributes / CLAUDE.md).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def canonical_json(obj: Mapping[str, Any]) -> str:
    """Serialize to canonical JSON: sorted keys, fixed float format, no whitespace
    variance. Standard content-addressing practice — spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    raise NotImplementedError(
        "canonical_json — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )


def idempotency_key(source_id: str, occurred_at: str, payload: Mapping[str, Any]) -> str:
    """SHA256(source_id || occurred_at || canonicalize(payload)).

    Source-scoped duplicate guard — spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    raise NotImplementedError(
        "idempotency_key — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )


def event_hash(envelope_minus_hash_fields: Mapping[str, Any], prev_event_hash: str | None) -> str:
    """SHA256(canonical_json(event_minus_hash_fields) || prev_event_hash).

    Tamper-evidence chain over ENVELOPE fields only (not payload), so a destroyed
    payload never breaks verification (Invariant 14). spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    raise NotImplementedError(
        "event_hash — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )


def dep_hash(dependency_event_hashes: Sequence[str]) -> str:
    """SHA256(sorted([event_hash for event in dependency_set])).

    Hashes the event_hashes (not ids) so the dependency hash also changes when an
    upstream event is *superseded*, not only when one disappears. Shared by the
    Liver (§3) and the process trace (§7) — spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    raise NotImplementedError(
        "dep_hash — implement when the Liver / process-trace lands; "
        "see spec/NYX_V0_IMPLEMENTATION.md §1"
    )
