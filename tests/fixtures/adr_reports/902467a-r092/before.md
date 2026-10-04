# ADR 0009: Projection Parameters — as_of, projector_version, projected_as_of



Status: Accepted

Date: 2026-09-07

Supersedes: nothing

Related: Invariant 9; GAPS.md (as_of and projector_version silently ignored)



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

## Rationale



A projector that appears to reconstruct the past while silently injecting the

present is the exact failure Nyx exists to prevent. The A/B split and

deterministic replay are load-bearing for that reason, not as architectural

taste. Recording this here so a future reader does not mistake ADR 0009 for a

technicality.



## Consequences



- project() honors both parameters or raises. It never silently ignores them.

- Same log plus same as_of plus same version yields a byte-identical view.

- Callers passing version "0" are unaffected.

- Historical-truth queries (bounding occurred_at) remain

