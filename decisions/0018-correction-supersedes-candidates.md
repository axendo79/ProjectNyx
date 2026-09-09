# ADR 0018: Corrections Supersede Explicit Candidates

Status: Accepted

Date: 2026-09-09

Supersedes: [ADR 0004](0004-correction-appended-supersedes-via-superseding-events.md), only the correction payload and supersession representation under projector version `"1"`.

Related: [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0015](0015-candidate-scoped-verification.md)

Implementation: Pending; implementation is a separate task.

## Context

A belief may hold several candidates with distinct support and verification
histories. A correction's new value alone does not identify which claims it
supersedes.

## Decision

A correction explicitly identifies the candidate IDs it supersedes. Source
lineage does not establish scope. The correction records a fresh candidate and
its targets. Each target is validated against the pre-event snapshot and recorded
in the payload so replay reproduces the same scope.

Superseded candidates are retained with their evidence and verification history.
Supersession is an explicit relation: it erases nothing and transfers no
verification to the new candidate, which earns its own standing from its own
evidence.

A correction naming no targets is underspecified and refuses. Introducing a new
value as an additional alternative is an ordinary observation, not a correction.

## Consequences

This adds a required field to the correction payload relative to ADR 0004. A
correction event without targets cannot be processed under projector version
`"1"`. Version `"0"` retains its existing correction semantics unchanged.

## Acceptance cases

Start with b-N holding c-A (64, verified), c-B (64, questioned), and c-C (128).

- **One target:** a correction asserting 32 records a fresh candidate and targets
  only c-A. It supersedes c-A; c-B and c-C remain alternatives. All prior candidates,
  evidence, and verification histories remain available. The new candidate earns
  its own standing without inheriting c-A's verification.
- **All targets:** a correction asserting 32 explicitly targets c-A, c-B, and c-C.
  It supersedes all three through recorded relations, retaining their evidence and
  verification histories. Its fresh candidate earns standing from its own evidence.
- **No targets:** a correction asserting 32 with no targets refuses before append
  without mutation. Replay under version `"1"` also refuses a recorded correction
  lacking targets; it does not treat the event as an ordinary observation.
