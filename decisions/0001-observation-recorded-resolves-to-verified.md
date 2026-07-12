# 0001 — An `observation_recorded` event resolves its belief to `verified`

- **Status:** Accepted — ratified by Josh, 2026-07-12
- **Date:** 2026-07-12
- **Scope:** Walking skeleton (commit two), `src/nyx/projection.py` `fold()`
- **Relates to:** Invariants 3, 4 · Architecture §2, §5 · V0 §6

## Context

The walking-skeleton acceptance test (`NYX_V0_IMPLEMENTATION.md` §6, lines 243–251)
asserts that submitting one `observation_recorded` event for `legion.ram = 64GB`
materializes the belief at `verification_state = "verified"`,
`verifiability = "externally_checkable"`.

This sits directly under two invariants that could be read to forbid it:

- **Invariant 3 (No Silent Promotion):** nothing moves toward `verified` without an
  *independent signal*; promotion may not fire on internal consistency alone.
- **Invariant 4 (Verification Domain Separation):** only a **world-oracle** class
  signal may raise confidence or promote world-truth state. Re-derivation from
  Layer A is explicitly *not* independent evidence about the world.

So: does landing a fresh observation at `verified` violate No Silent Promotion?

## Decision

No. An `observation_recorded` event carries a **world-oracle-class signal by
construction**, so it may land its belief at `verified`. `projection.fold()`
implements this for the `observation_recorded` handler and cites the reasoning
inline (`resolution_basis = "direct observation (world-oracle class, Inv. 4)"`).

## Rationale

Architecture §5 (line 204) enumerates the world-oracle class as *"human
confirmation, **direct observation**, independent external re-check."* A direct
observation **is** the independent signal — it is not the system re-deriving a
belief from its own log (which would be a derivation-validator signal, barred from
promotion by Inv. 4). There is therefore no *silent* promotion: the promotion is
carried by an external, world-oracle input, which is exactly what Inv. 3 requires.

The distinction that keeps this honest:

- `observation_recorded` (origin `observed`) → world-oracle class → **may** verify.
- A Layer B `derived` statement re-entering as support → derivation-validator →
  **may not** verify (must route the normal gated path; see also Inv. 15).

Nothing here lets confidence create evidence (Inv. 2): the evidence is the
observation event itself, durably in Layer A.

## Consequences

- The §6 acceptance test is satisfiable without weakening any invariant.
- Not every origin type inherits this. `user_stated` splits into *"user asserted X"*
  vs *"X is true"* (§2) and does **not** verify the latter without independent
  support; `derived` is not stored by default. Those handlers, when written, must
  make their own origin-appropriate state call — they do **not** copy this one.
- The `verifiability` value (`externally_checkable`) is carried on the observation's
  payload, not inferred — it is a property of the claim, not of the origin type.

## Alternatives considered

- **Land observations at `unverified`, require a separate oracle event to reach
  `verified`.** Rejected: it treats a direct observation as if it were a mere
  derivation, contradicting the §5 world-oracle enumeration, and it makes the §6
  acceptance test (as written in the spec) unsatisfiable. If this is ever revisited,
  it is a *spec* change to §5/§6, not a quiet implementation tweak — record a new
  ADR that supersedes this one.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
