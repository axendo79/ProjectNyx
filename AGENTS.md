# ProjectNyx - Agent Instructions

Runtime: Python 3.14.2 in .venv. Tests: run the full pytest suite (`pytest -q`); all tests must pass.

## Authority
- spec/NYX_ARCHITECTURE.md is authoritative for what and why.
- spec/NYX_V0_IMPLEMENTATION.md is authoritative for how: schema, algorithms, defaults, tests.
- Accepted ADRs in decisions/[0-9][0-9][0-9][0-9]-*.md supersede the spec where they conflict.
- GAPS.md lists logged, not-yet-fixed findings. Do not fix a gap outside your task scope.
- CLAUDE.md was written for a different agent. Ignore it.

Accepted specifications and ADRs govern implementation. Material under `design/` is non-authoritative and may be analyzed or drafted when requested. It does not authorize implementation, supply missing defaults, or supersede accepted decisions. When implementation requires an unresolved decision, stop the dependent work and report it. Ratification must be recorded explicitly before implementation proceeds.

## Standing rule
The spec is complete. Build it, do not redesign it. Never edit anything under
spec/ or decisions/. If you believe the spec is wrong, stop and report it;
do not implement your alternative.

## Gap protocol
If the spec is silent on a decision your task requires, STOP and report the gap.
Do not infer, do not pick a reasonable default, do not leave a placeholder. A
halted task with a clearly stated gap is a success. A completed task built on a
guessed decision is a failure that costs more to unwind than it saved.

Halt cases (NYX_V0_IMPLEMENTATION.md section 7): backdated corrections;
origin-to-state transitions beyond observed; anything requiring the fold
signature to handle cross-belief events, which is blocked on ADR 0008.

## Invariants
Event-sourced store. Layer A is append-only. fold is equivalent to
replay-from-genesis, an executable invariant rather than an aspiration. Any
change that makes replay non-deterministic is wrong regardless of what it fixes.