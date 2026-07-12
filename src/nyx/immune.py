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
from typing import Any, Mapping


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
    the walking skeleton needs. Implement in commit 2.
    """
    raise NotImplementedError(
        "stage1_schema_validate — implement in walking skeleton; "
        "see spec/NYX_V0_IMPLEMENTATION.md §6, spec/NYX_ARCHITECTURE.md §3"
    )


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
