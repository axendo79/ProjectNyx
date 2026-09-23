# ADR 0010: Projection Parameters — as_of, projector_version, projected_as_of



Status: Accepted; superseded in part by [ADR 0030](0030-sole-writer-and-positional-fields.md), only section 1a's ordinary writer timestamp assignment and its backward-clock refusal acceptance case.

**Numbering history (2026-09-08):** This ADR was originally committed and referenced as 0009. It was renumbered to 0010 to distinguish it from the Python-target ADR, which retains 0009. Commit history will continue to refer to this projection-parameters decision as 0009.

Date: 2026-09-07

Supersedes: nothing

Related: Invariant 9; GAPS.md (as_of and projector_version silently ignored)

Implementation: `projection.project` and `project_snapshot` apply inclusive `recorded_at` cutoffs and dispatch the registered projector; "0", "1" and "2" now ship, with "0" still the default. Reducers receive explicit evaluation time, and belief `updated_at` comes from its last included contributing event. Low-level append integrity checks refuse supplied pairs with backward recording times; ADR 0030's ordinary writer assignment and clock checks are accepted but pending implementation. Coverage of the shipped behavior is in `tests/test_projection_parameters.py`, `tests/test_recorded_at_monotonicity.py` and the stage-two suites. Checked 2026-09-13; the ignored-parameter and ADR 0008 blocker descriptions below record the decision-time state.



## Context



project() accepts as_of and projector_version and ignores both. Invariant 9

requires Resolved View = project(log, as_of, version), so the current signature

promises a guarantee the implementation does not provide. This is the most

deceptive gap in the register: callers cannot tell that their arguments do

nothing.



Implementation was blocked on three unspecified decisions, recorded here

together because they are one decision about what a projection is.



Separately, the fold algorithm sets projected_as_of = now(). This contradicts

fold is equivalent to replay-from-genesis: replaying an identical log twice

produces different output. This ADR treats that as in scope.



## Decision



### 1. as_of bounds recorded_at, inclusive



An event is included in a projection when recorded_at <= as_of.



occurred_at is a claim carried in the payload and a later correction may assert

a different occurred_at for the same fact. Bounding on it would make a

historical view depend on knowledge that arrived after the moment being

reconstructed. recorded_at is a property of the log, monotonic, never revised.



Where multiple events share a recorded_at value, they are ordered by the

existing sequence and hash-chain order. The projector introduces no additional

ordering rule.



as_of earlier than the genesis event yields an empty view. No knowledge had

been recorded.



Accepted consequence: this design answers "what did we know at time T." It does

not answer "what was true at time T." That is a different query and would be a

separate parameter, not a redefinition of this one.



### 1a. Append enforces recorded_at monotonicity.

As amended by [ADR 0030 sections 4 and 5](0030-sole-writer-and-positional-fields.md#4-write-time-clock-checks-and-bounded-clamping),
the ordinary writer assigns recorded_at under the append lock. Sample 1 checks
the unadjusted clock: refuse if `tip.recorded_at - sample_1 > 120 s`. Exactly
120 seconds is permitted. After that check, assign
`recorded_at = max(sample_1, tip.recorded_at)`, comparing offset-bearing instants;
at genesis assign sample 1. There is no increment; equal timestamps remain legal
and retain insertion/hash-chain order. Sample 2, taken after assignment and before
insertion, is validation only: refuse if `recorded_at - sample_2 > 120 s`.
The threshold is a named writer constant, not runtime configuration; changing
it requires an ADR amendment.

Recorded_at is never earlier than sample 1 or the predecessor's recorded_at.
During tolerated backward-clock skew it may be ahead of the writer's observed
wall clock by at most 120 seconds at these checks. This establishes no claim
about true recording time or trustworthy UTC. Refusal is synchronous and typed,
carrying the fields and units in ADR 0030 section 5. Recovery is automatic with
no latch: every attempt, including after restart, rechecks the persisted tip and
both clock conditions under the append lock.

Assignment occurs only before first commitment. Committed timestamps remain
immutable and monotonically nondecreasing; no committed event is reordered or
rewritten. Low-level integrity checks still refuse a supplied pair whose
recorded_at precedes the committed tip; they do not repair prepared or committed
envelopes. Recording-time cutoffs and the backdated-correction rule are unchanged.

### 2. projector_version is a registry; unsupported versions fail loud



Supported values: "0" — the current fold implementation. String, not integer.



An unsupported version raises. It does not fall back to the newest projector.

Silent fallback would let a replay pinned to an old version quietly produce

new-version output, which is the same class of deception this ADR exists to

remove.



Versions are held in a mapping from version string to fold implementation, so

adding a version is additive rather than a growing conditional.



### 3. projected_as_of is the as_of parameter, never now()



projected_as_of is set to the as_of value the projection was called with. For a

live projection as_of defaults to the current time, so behavior in the common

path is unchanged. For a replay it is the historical cutoff.



The field means the evaluation point the view represents, not the wall-clock

moment the computation ran. Computation time is telemetry and does not belong

in a projected value that an executable invariant compares.



### 3a. updated_at is the recorded_at of the last included event.



updated_at is set to the recorded_at of the last event included in the

projection, not now(). It records when the view last changed, which is a

property of the log rather than of the computation. For an empty view

(as_of earlier than genesis), updated_at is null.



### 3b. fold takes an explicit evaluation time.

fold accepts the evaluation time as a parameter rather than calling now().
The live write path passes the current time at the call site; a replay passes
the as_of cutoff. This is an additive parameter and does not change fold's
one-belief-in, one-belief-out shape, which remains blocked on ADR 0008.

The prohibition on changing the fold signature refers to that shape, not to
adding an evaluation-time parameter.

## Acceptance tests

- **Backward clock adjustment at append:** with an injected clock and threshold,
  a tip exactly 120 seconds ahead of sample 1 is within tolerance; assignment
  clamps to the tip without an increment. A tip 120 seconds plus epsilon ahead
  refuses before assignment or append. Equal timestamps preserve hash-chain
  ordering. A sample-2 backward step beyond the threshold refuses before
  insertion without changing Layer A. Restart rechecks the persisted tip;
  appends resume automatically only when both checks pass. Committed timestamps
  are never rewritten. Low-level checks still refuse supplied backward pairs.

## Rationale



A projector that appears to reconstruct the past while silently injecting the

present is the exact failure Nyx exists to prevent. The A/B split and

deterministic replay are load-bearing for that reason, not as architectural

taste. Recording this here so a future reader does not mistake ADR 0010 for a

technicality.



## Consequences



- project() honors both parameters or raises. It never silently ignores them.

- Same log plus same as_of plus same version yields a byte-identical view.

- Callers passing version "0" are unaffected.

- Historical-truth queries (bounding occurred_at) remain
