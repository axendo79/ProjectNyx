"""Immune system — prevent bad data entering (defense-in-depth, tiered cascade).

spec/NYX_ARCHITECTURE.md §3. No single layer is trusted alone (single-layer
prompt-injection detectors have been evaded at rates up to 100%). Rejections at
ANY stage are logged events — a silently-dropping gate is unauditable.

Walking skeleton (spec/NYX_V0_IMPLEMENTATION.md §6) uses Stage 1 ONLY; Stages 2–4
are stubbed. Stage 2/3/4 wiring is §8 (still open) — STOP-and-fail-loud, do not
invent a classifier invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

# Required keys for a skeleton observation (spec/NYX_V0_IMPLEMENTATION.md §6).
_REQUIRED = ("belief_id", "value", "verifiability", "occurred_at", "source", "source_class")


@dataclass(frozen=True)
class ImmuneResult:
    """Outcome of the cascade. A rejection must still be RECORDED as an event
    (spec/NYX_ARCHITECTURE.md §3) — accepted=False is not a silent drop."""

    accepted: bool
    stage_reached: int
    reason: str | None = None


def stage1_schema_validate(raw: Mapping[str, Any]) -> ImmuneResult:
    """Stage 1 (deterministic, ~0 cost): schema validation + regex for temporal/
    structural impossibilities. spec/NYX_ARCHITECTURE.md §3. This is the ONLY stage
    the walking skeleton needs.

    Deterministic gate: required fields present, occurred_at a parseable ISO8601
    instant (a structural impossibility check). Rejections must ultimately be
    logged events (§3); the skeleton surfaces the rejection to the caller, and the
    reject-and-RECORD event path is a later slice (§8), not part of §6's happy path.
    """
    for key in _REQUIRED:
        if key not in raw or raw[key] in (None, ""):
            return ImmuneResult(accepted=False, stage_reached=1, reason=f"missing field: {key}")
    source = raw.get("source")
    if not isinstance(source, Mapping) or not source.get("actor_id"):
        return ImmuneResult(accepted=False, stage_reached=1, reason="source.actor_id required")
    try:
        datetime.fromisoformat(str(raw["occurred_at"]))
    except ValueError:
        return ImmuneResult(accepted=False, stage_reached=1, reason="occurred_at not ISO8601")
    return ImmuneResult(accepted=True, stage_reached=1)


def stage2_classifier(raw: Mapping[str, Any]) -> ImmuneResult:
    """Stage 2 (small CPU classifier, Prompt-Guard-class). Wiring UNDECIDED — §8."""
    raise NotImplementedError(
        "Immune Stage 2 wiring undecided — see spec/NYX_V0_IMPLEMENTATION.md §8"
    )


def stage3_stlm(raw: Mapping[str, Any]) -> ImmuneResult:
    """Stage 3 (STLM, non-resident). Ships STATIC in v0 — no retraining loop until
    a threat corpus exists (spec/NYX_ARCHITECTURE.md §3). Wiring UNDECIDED — §8."""
    raise NotImplementedError(
        "Immune Stage 3 wiring undecided — see spec/NYX_V0_IMPLEMENTATION.md §8"
    )


def stage4_llm(raw: Mapping[str, Any]) -> ImmuneResult:
    """Stage 4 (LLM / Nyx Jr) — only payloads surviving Stages 1–3 reach here. The
    survivor gets the affect split (Invariant 11). Wiring UNDECIDED — §8."""
    raise NotImplementedError(
        "Immune Stage 4 wiring undecided — see spec/NYX_V0_IMPLEMENTATION.md §8"
    )
