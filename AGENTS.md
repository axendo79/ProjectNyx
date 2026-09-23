# ProjectNyx - Agent Instructions

Runtime: Python 3.14.2 in .venv. Tests: run the full pytest suite (`pytest -q`); all tests must pass.

## Authority
- spec/NYX_ARCHITECTURE.md is authoritative for what and why.
- spec/NYX_V0_IMPLEMENTATION.md is authoritative for how: schema, algorithms, defaults, tests.
- Accepted ADRs in decisions/[0-9][0-9][0-9][0-9]-*.md supersede the spec where they conflict.
- GAPS.md lists findings and their open or resolved status. Do not fix a gap outside your task scope.
- CLAUDE.md was written for a different agent. Ignore it.

Accepted specifications and ADRs govern implementation. Material under `design/` is non-authoritative and may be analyzed or drafted when requested. It does not authorize implementation, supply missing defaults, or supersede accepted decisions. When implementation requires an unresolved decision, stop the dependent work and report it. Ratification must be recorded explicitly before implementation proceeds.

## Required reading order
Before consulting specification mechanics, read in this order:

1. [README.md](README.md) for shipped state and the [decision-to-code map](README.md#decision-to-code-map).
2. The applicable numbered ADR chain, including referenced amendments and superseding ADRs. An ADR's **Status** line governs its standing; use its **Implementation** line for current implementation status. Body text may describe decision-time state and must be read subject to those status markers and later accepted ADRs.
3. [NYX_ARCHITECTURE.md](spec/NYX_ARCHITECTURE.md), then [NYX_V0_IMPLEMENTATION.md](spec/NYX_V0_IMPLEMENTATION.md), subject to that ADR chain. Check [GAPS.md](GAPS.md) before dependent implementation; silence in a specification alone does not establish a gap until the applicable ADRs have been read.

For merge work, the required chain is [ADR 0013](decisions/0013-cross-belief-identity-semantics.md), then [ADR 0014](decisions/0014-cross-belief-reducer-and-hash-lineage.md) as amended by [ADR 0015](decisions/0015-candidate-scoped-verification.md), with stage limits in [ADR 0023](decisions/0023-stage-two-contract.md).

## Standing rule
Build the accepted specifications and ADRs; do not redesign them or fill unresolved decisions. Never edit anything under
spec/ or decisions/. If you believe the spec is wrong, stop and report it;
do not implement your alternative.

## ADR commit protocol
For every future ADR, keep authority and implementation changes separate.
When the maintainer explicitly authorizes authority edits, use this protocol:

- **(A) Authority:** all edits under decisions/ and spec/. Stage only the
  authorized authority change, show `git status --short` and `git diff --cached`,
  then stop. The maintainer commits it; wait for their confirmation before
  continuing with implementation. Never commit authority files yourself.
- **(B) Implementation:** code, tests, README, GAPS and other non-authority docs.
  A (B) change never edits decisions/ or spec/. After the maintainer confirms
  the authority commit, implement, validate and commit only (B) files.
- After each (B) commit, stage a separate one-line (A) change marking that ADR's
  Implementation complete and citing the (B) commit hash. Show the status and
  staged diff, then stop for the maintainer's commit. Never include this marker
  in the implementation commit.
- Before every commit, inspect `git status --short` and the staged diff.
  Never mix different ADRs' work in one commit; finish each ADR in dependency order.
- Never use `--no-verify` or otherwise bypass a commit hook. If a hook refuses
  a commit, stop and report its output; do not work around it.

## Gap protocol
If the spec is silent on a decision your task requires, STOP and report the gap.
Do not infer, do not pick a reasonable default, do not leave a placeholder. A
halted task with a clearly stated gap is a success. A completed task built on a
guessed decision is a failure that costs more to unwind than it saved.

Halt cases (NYX_V0_IMPLEMENTATION.md section 7): backdated corrections;
origin-to-state transitions beyond observed; unspecified cross-belief verification
transitions. ADR 0014 supersedes ADR 0008; its reducer seam, lineage, progress,
publication, and recovery are implemented for stage two under projector "1".
For the superseded differing-state merge refusal, see
[ADR 0015](decisions/0015-candidate-scoped-verification.md).
Merge and split handlers remain unimplemented; current stage limits are governed by
[ADR 0023](decisions/0023-stage-two-contract.md).

## Invariants
Event-sourced store. Layer A is append-only. fold is equivalent to
replay-from-genesis, an executable invariant rather than an aspiration. Any
change that makes replay non-deterministic is wrong regardless of what it fixes.
