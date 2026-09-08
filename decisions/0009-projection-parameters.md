\# ADR 0009: Projection Parameters — as\_of, projector\_version, projected\_as\_of



Status: Accepted

Date: 2026-09-07

Supersedes: nothing

Related: Invariant 9; GAPS.md (as\_of and projector\_version silently ignored)



\## Context



project() accepts as\_of and projector\_version and ignores both. Invariant 9

requires Resolved View = project(log, as\_of, version), so the current signature

promises a guarantee the implementation does not provide. This is the most

deceptive gap in the register: callers cannot tell that their arguments do

nothing.



Implementation was blocked on three unspecified decisions, recorded here

together because they are one decision about what a projection is.



Separately, the fold algorithm sets projected\_as\_of = now(). This contradicts

fold is equivalent to replay-from-genesis: replaying an identical log twice

produces different output. This ADR treats that as in scope.



\## Decision



\### 1. as\_of bounds recorded\_at, inclusive



An event is included in a projection when recorded\_at <= as\_of.



occurred\_at is a claim carried in the payload and a later correction may assert

a different occurred\_at for the same fact. Bounding on it would make a

historical view depend on knowledge that arrived after the moment being

reconstructed. recorded\_at is a property of the log, monotonic, never revised.



Where multiple events share a recorded\_at value, they are ordered by the

existing sequence and hash-chain order. The projector introduces no additional

ordering rule.



as\_of earlier than the genesis event yields an empty view. No knowledge had

been recorded.



Accepted consequence: this design answers "what did we know at time T." It does

not answer "what was true at time T." That is a different query and would be a

separate parameter, not a redefinition of this one.



\### 2. projector\_version is a registry; unsupported versions fail loud



Supported values: "0" — the current fold implementation. String, not integer.



An unsupported version raises. It does not fall back to the newest projector.

Silent fallback would let a replay pinned to an old version quietly produce

new-version output, which is the same class of deception this ADR exists to

remove.



Versions are held in a mapping from version string to fold implementation, so

adding a version is additive rather than a growing conditional.



\### 3. projected\_as\_of is the as\_of parameter, never now()



projected\_as\_of is set to the as\_of value the projection was called with. For a

live projection as\_of defaults to the current time, so behavior in the common

path is unchanged. For a replay it is the historical cutoff.



The field means the evaluation point the view represents, not the wall-clock

moment the computation ran. Computation time is telemetry and does not belong

in a projected value that an executable invariant compares.



\## Rationale



A projector that appears to reconstruct the past while silently injecting the

present is the exact failure Nyx exists to prevent. The A/B split and

deterministic replay are load-bearing for that reason, not as architectural

taste. Recording this here so a future reader does not mistake ADR 0009 for a

technicality.



\## Consequences



\- project() honors both parameters or raises. It never silently ignores them.

\- Same log plus same as\_of plus same version yields a byte-identical view.

\- Callers passing version "0" are unaffected.

\- Historical-truth queries (bounding occurred\_at) remain

