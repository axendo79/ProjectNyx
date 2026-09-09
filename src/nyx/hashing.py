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

import hashlib
import json
from typing import Any, Mapping, Sequence

# Field separator for concatenated hash material. A fixed, non-printable delimiter
# so ("ab","c") and ("a","bc") never collide — a v0 disambiguation of the spec's
# `||` concatenation (spec §1). Internal-only (idempotency dedup within one DB), so
# a stable separator is safe and strictly more correct than bare concatenation.
_SEP = "\x1f"


def canonical_json(obj: Any) -> str:
    """Serialize to canonical JSON: sorted keys, compact separators, no whitespace
    variance. Standard content-addressing practice — spec/NYX_V0_IMPLEMENTATION.md §1.
    (Python's float repr is shortest-round-trip and deterministic; the skeleton
    carries no floats. A stricter fixed float format is a later concern, not needed
    to start — §3 defer-don't-invent.)
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_set(members: Sequence[Any]) -> list[Any]:
    """ADR 0014: deduplicate sets and order by canonical UTF-8 bytes.

    Call only for collections with set semantics; recorded sequences (including
    edges within a provenance path) retain their order.
    """
    encoded = {canonical_json(member).encode("utf-8"): member for member in members}
    return [encoded[key] for key in sorted(encoded)]


def belief_lineage(
    projector_version: str,
    event_id: str,
    event_digest: str,
    predecessors: Sequence[Mapping[str, Any]],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """ADR 0014 lineage record, distinct from Layer A's unchanged hashing.

    Result collections must already be canonical in the projected result. The
    current ordinary-event reducer has only one evaluation-only field.
    """
    return {
        "lineage_format": "nyx-belief-lineage/1",
        "projector_version": projector_version,
        "producing_event": {"event_id": event_id, "event_hash": event_digest},
        "predecessors": canonical_set(predecessors),
        "result": {key: value for key, value in result.items()
                   if key not in ("view_version_hash", "projected_as_of")},
    }


def _sha256_hex(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def idempotency_key(source_id: str, occurred_at: str, payload: Mapping[str, Any]) -> str:
    """SHA256(source_id || occurred_at || canonicalize(payload)).

    Source-scoped duplicate guard — spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    return _sha256_hex(_SEP.join([source_id, occurred_at, canonical_json(payload)]))


def event_hash(envelope_minus_hash_fields: Mapping[str, Any], prev_event_hash: str | None) -> str:
    """SHA256(canonical_json(event_minus_hash_fields) || prev_event_hash).

    Tamper-evidence chain over ENVELOPE fields only (not payload), so a destroyed
    payload never breaks verification (Invariant 14). The genesis link uses the
    empty string for a missing prev hash. spec/NYX_V0_IMPLEMENTATION.md §1.
    """
    return _sha256_hex(canonical_json(envelope_minus_hash_fields) + (prev_event_hash or ""))


def dep_hash(dependency_event_hashes: Sequence[str]) -> str:
    """SHA256(sorted([event_hash for event in dependency_set])).

    Hashes the event_hashes (not ids) so the dependency hash also changes when an
    upstream event is *superseded* (new event_hash chained on), not only when one
    disappears. Shared by the Liver (§3) and the process trace (§7).
    """
    return _sha256_hex(canonical_json(sorted(dependency_event_hashes)))
