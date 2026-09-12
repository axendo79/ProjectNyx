# ADR 0026: Usage Is Not Evidence

Status: Accepted

Date: 2026-09-12

Related: [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md); [ADR 0025](0025-incremental-result-commitment.md); architecture Invariants 2, 4, 7, and 8; [temporal and activation direction](../design/temporal-activation-direction.md)

Implementation: Binding boundary; no usage-log or activation subsystem is implemented by this decision.

## Context

Dream, retrieval, and activation can generate frequent usage records. Frequency
of use describes system behavior and does not establish additional world evidence.
The unratified activation direction leaves the recording location unresolved.

## Decision

Dream references, retrieval exposures, and activation records never become
evidence dependencies of a belief and never enter its lineage. Usage is recorded
separately from world truth. Repeated use creates neither corroboration nor new
ClaimCandidates and does not change verification or belief lineage.

This boundary binds `design/temporal-activation-direction.md`. Its operational
recording location must respect this separation; the design document supplies
no exception. A usage record may identify the belief or event used, but that
reference does not become an evidence edge back into the belief. An independently
accepted world observation remains an observation even when Dream initiated the
check; the act of referring to or exposing existing content is not that signal.

## Consequences

The physical usage-log schema, durability authority, ordering, retention,
configuration versioning, recovery, and replay scope require later decisions,
including resolution of the activation direction's Invariant 8 tension. This ADR
authorizes no new operational log and no silent skipping of unsupported usage
events inserted into the world-event stream. Existing projector refusals remain.

## Acceptance cases

- Repeated exposure, reference, or activation supplies no evidence membership,
  candidate, verification change, or new belief lineage.
- Usage can point to world records without becoming their supporting evidence.
- Future activation implementations preserve this boundary and separately decide
  their operational storage contract; unresolved mechanics gain no defaults here.
