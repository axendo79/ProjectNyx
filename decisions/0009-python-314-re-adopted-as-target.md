# 0009 — Python 3.14 re-adopted as the target (the downgrade P0 was never enforced)

- **Status:** Accepted — ratified by Josh, 2026-07-15
- **Date:** 2026-07-15
- **Scope:** `CLAUDE.md` (Environment), `spec/NYX_ARCHITECTURE.md` §402 (P0 list),
  `GAPS.md` (Python-version note)
- **Relates to:** `spec/HANDOFF_2026-07-11.md` (the re-sequenced P0 list),
  [ADR 0004](0004-correction-appended-supersedes-via-superseding-events.md) (where the
  discrepancy was first logged)

## Context

Two documents disagreed about the Python version, and the disagreement had gone unresolved
since it was logged in ADR 0004:

- `NYX_ARCHITECTURE.md` §402 lists **"Python 3.14→3.11/3.12"** as a re-sequenced **P0 fix** —
  a deliberate decision to walk the earlier 3.14 target *back* to 3.11/3.12.
- `CLAUDE.md` faithfully reflected that: *"Python 3.11/3.12 (the spec's earlier 3.14 target
  was walked back — see handoff)."*
- **The runtime, however, is 3.14.2.** It is the *only* interpreter installed on the build
  machine (`py -0p` lists nothing else), and the full suite (19 tests) is green on it.

So the docs were not stale about *intent* — they recorded a real decision. What never
happened was the **enforcement** of that decision: no 3.11/3.12 interpreter was ever
installed, no version pin or CI guard was added, and because nothing in v0 yet depends on a
3.11/3.12-only behavior, the unenforced downgrade never bit. The P0 was carried as intent and
silently ignored in practice.

This is not the two-file provenance case (where `NYX_V0_IMPLEMENTATION.md`'s mechanical
statement wins over prose). It is a plain intent-vs-reality gap: a P0 in the authoritative
architecture doc that the environment never satisfied.

## Decision

**Re-adopt Python 3.14 as the target.** Reality wins here because the reasons that would have
justified holding 3.11/3.12 are absent:

- Nothing in the codebase uses a 3.14-only feature that would strand us on it, *and* nothing
  requires 3.11/3.12 — the suite passes on 3.14 as-is, so there is no compatibility debt to
  pay down by downgrading.
- The downgrade P0 carried no recorded rationale beyond "walked back" — no library
  incompatibility, no support-window argument, no reproducibility concern was ever attached
  to it. An unmotivated P0 that the environment already contradicts is not worth enforcing
  against a green suite.
- Hash determinism — the project's one hard cross-machine reproducibility requirement — is
  guarded at the data layer (canonical JSON) and by `.gitattributes` (LF), **not** by the
  interpreter minor version. Changing the target Python does not touch `fold ≡
  replay-from-genesis`.

Concretely: `CLAUDE.md` now says **Python 3.14**; §402's downgrade P0 is struck through and
annotated as superseded by this ADR; the `GAPS.md` note is marked RESOLVED.

## Consequences

- **Docs now match reality.** The next reader is not told to target a Python that no machine
  in this project runs.
- **The floor is 3.14, not a range.** We are deliberately *not* re-adopting the old "3.14"
  *plus* a promise of 3.11/3.12 compatibility. If broad-version support is wanted later, that
  is a new decision with its own testing (a version matrix in CI), not an implicit carry-over.
- **No code changes.** This is a documentation reconciliation; the suite was already green on
  3.14 and stays 19-green.
- **Enforcement is now the open item, not the version choice.** There is still no pin
  (`requires-python`, a CI Python-version guard) that would make this target *binding* rather
  than merely documented — the same class of gap that let the original P0 go unenforced. That
  belongs on the list before a second contributor or a CI runner joins; it is logged, not
  fixed here.

## Alternatives considered

- **Hold 3.11/3.12 and pin the environment down to it** (install the interpreter, add a
  version guard). Rejected: it enforces an unmotivated downgrade against a green suite, and
  spends effort making reality *worse*-supported to honor a P0 that no longer has a stated
  reason. If a concrete 3.11/3.12 requirement surfaces (a deployment target, a dependency
  floor), this is reversible with its own ADR.
- **Leave both documents as-is and keep the note in GAPS.** Rejected: it perpetuates a
  standing contradiction between the authoritative architecture doc and the running
  environment, which is exactly the kind of latent trap the gap register exists to *close*,
  not to host indefinitely.
- **Silently change `CLAUDE.md` to 3.14 without touching §402.** Rejected: it would leave the
  architecture doc (authoritative for *what/why*) still ordering a downgrade, so the
  contradiction would move rather than resolve — and it would be an unrecorded override of a
  P0, which the build discipline forbids.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
