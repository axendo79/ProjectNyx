# ADR 0012: Whole-View Equality

Status: Accepted

Date: 2026-09-08

Related: [ADR 0010](0010-projection-parameters.md); Invariant 9

Implementation: Pending; implementation is a separate task.

## Context

The live write path supplies a call-time evaluation timestamp to each fold and
updates only the affected belief. Beliefs updated at different times therefore
retain different `projected_as_of` values. Full replay at one cutoff assigns that
cutoff to every included belief. Comparing raw materialized rows with that replay
can differ in timestamps even when belief values and version hashes match.

## Decision

Whole-view equality holds at an explicit shared evaluation time T. For the same
log, cutoff T, and projector version, the complete view evaluated through the
incremental/materialized path must equal the complete view produced by replay at
T. Equality includes `projected_as_of` and all other projected fields, not only
belief values or hashes.

Raw materialized rows are not automatically a whole-view snapshot at one time.
Their individual evaluation timestamps do not establish that the collection has
been evaluated at a shared T. Comparing those raw rows directly with a replay at
T does not establish the required whole-view equality.

Hash-only comparison is insufficient because it conceals the timestamp
discrepancy. The contract is not weakened by dropping timestamps or other fields
from the comparison.

Normalizing `projected_as_of` to T may suffice for the current reducer, where the
evaluation-time argument only supplies that field. Such normalization is valid
only when the remaining projected fields already represent the same log cutoff
and projector version at T. Relabeling rows that include events after T does not
produce a historical view.

Future time-dependent behavior must be evaluated at T rather than relabeled.
If decay, state, ranking, or any other projected field depends on evaluation time,
that behavior must be evaluated using T before the whole view is compared with
replay. Timestamp normalization alone is not a general evaluation algorithm.

## Consequences

This decision resolves the equality-contract ambiguity without requiring every
raw materialized row to share a timestamp after each individual live write.
It does not select a public API, cache-update strategy, or normalization algorithm.
Implementation and executable acceptance coverage remain a separate task.

ADR 0010's recording-time cutoff, projector-version selection, and per-fold
explicit evaluation-time rules remain in force. The cross-belief event-shape and
hash-lineage blocker in ADR 0008 is separate and remains open. Layer A is unchanged.

## Acceptance tests

- **Multiple live evaluation times:** update belief A at T1 and belief B at T2.
  Confirm their raw materialized timestamps can differ and are not represented as
  a whole-view snapshot at one shared time merely because both rows exist.
- **Shared-time whole-view equality:** evaluate that multi-belief view at an
  explicit T and compare its complete canonical serialization with full replay
  of the same log at T using the same projector version. Every projected field,
  including `projected_as_of`, must match.
- **Timestamp discrepancy is observable:** two views with matching belief values
  and hashes but different `projected_as_of` values fail the complete-view equality
  assertion. Hash equality alone does not pass this acceptance test.
- **Historical cutoff:** include an event recorded after T. Evaluation at T agrees
  with replay at T and excludes its effects; relabeling the latest materialized
  rows cannot satisfy this test.
- **Current time-independent fields:** when only the evaluation time changes and
  the included log and projector version remain the same, the current reducer's
  non-time-dependent fields remain unchanged and `projected_as_of` equals T.
- **Time-dependent evaluation:** use a controlled time-dependent projector fixture
  whose output differs between T1 and T2. Evaluation at T2 recomputes that output
  and matches replay at T2; changing only the timestamp must fail. This fixture
  does not introduce production decay or ranking behavior.
- **Determinism and Layer A immutability:** repeating whole-view evaluation with
  the same log, explicit T, and version produces byte-identical output without
  modifying the event log.
