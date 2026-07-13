# 0006 — `occurred_at` comparison is instant-based, never lexical

- **Status:** Accepted — ratified by Josh, 2026-07-13
- **Date:** 2026-07-13
- **Scope:** `src/nyx/projection.py` (`_instant`, `fold`'s value-recency guard,
  `assert_not_backdated`), `tests/test_occurred_at_ordering.py`
- **Relates to:** V0 §1 (value-recency guard, "reducer value-resolution keys on
  `occurred_at`"), §5 trace 2 (reconnection seam), §6 (replay determinism) ·
  [decisions/0004](0004-correction-appended-supersedes-via-superseding-events.md) ·
  [decisions/0005](0005-backdated-corrections-fail-loud-pending-semantics.md)

## Context

Every value-setting decision in the system rests on one comparison — is this event's
`occurred_at` older than the value currently held? It governs:

- the **§1 value-recency guard** (`projection.fold`): supersede the head, or fold as
  provenance only?
- the **backdated-correction refusal** (`assert_not_backdated`, decisions/0005).

Both compared raw ISO8601 **strings**. Lexical order over ISO8601 text is not
chronological order once offsets vary, so the guard was corruptible in **both
directions**:

| `occurred_at` | true instant | vs. `2026-07-12T12:00:00Z` | lexical says |
|---|---|---|---|
| `2026-07-12T09:00:00-05:00` | `14:00Z` | **2h LATER** | earlier (`09…` < `12…`) |
| `2026-07-12T13:00:00+05:00` | `08:00Z` | **4h EARLIER** | later (`13…` > `12…`) |
| `2026-07-12T00:00:00+00:00` | same as `…T00:00:00Z` | **EQUAL** | earlier (`+` 0x2B < `Z` 0x5A) |

Consequences, all three demonstrated red before the fix:

1. A **valid** correction at a later instant was **refused** as backdated — the error
   text asserting it "predates the value it corrects" when it postdated it by two hours.
2. A **genuinely backdated** correction **sailed through** and silently took the head —
   the precise silent wrong answer decisions/0005 was written to prevent, walking past
   the guard meant to stop it.
3. The **same instant spelled two ways** compared unequal, so a value-setting event
   failed to update the value purely because of how its timestamp was written.

Failures 1 and 2 are corruptions in *opposite* directions — no one-sided sanity check
would have caught this.

## Decision

**`occurred_at` ordering is chronological, never lexical.** A helper, `_instant()`, parses
to a UTC-aware `datetime`, and **every** `<` comparison of `occurred_at` goes through it —
both sites, not one.

**Stored strings are never rewritten.** `occurred_at` sits inside the hashed envelope, so
canonicalizing it at rest would change every `event_hash` and break
`fold == replay-from-genesis` (§6). Normalization happens at the point of comparison and
nowhere else.

**Naive (offset-less) timestamps are refused, not assumed to be UTC.** Their instant is
genuinely unknown, and silently picking one would reintroduce exactly the class of quiet
wrong answer this ADR removes.

## Why it passed 13 tests

This is the part worth internalizing. Every fixture in the suite used one fixed format
(`+00:00`, UTC). Under a single format, lexical order *is* chronological order — so the
tests agreed with the bug. They never varied the one thing the defect depended on.

**Passing tests were evidence of nothing here.** The corruption was latent, not absent:
it would have surfaced the first time a real source emitted `Z` (overwhelmingly common),
or any non-UTC offset (any user-supplied or foreign-system timestamp). A suite can only
falsify what it varies.

Sharper still: decisions/0005 built a fail-loud guard *specifically* to prevent silent
wrong answers about backdated corrections — and shipped it standing on a comparison that
both refused valid corrections and admitted invalid ones. The guard was green, well
documented, and wrong. Depth of reasoning about a mechanism is not a substitute for
varying its inputs.

## Consequences

- 16 tests green (3 new ordering tests + the existing 13).
- No stored data changes; no event or view hash changes. The fix is comparison-time only.
- `_instant()` is the single chokepoint. Any future `occurred_at` comparison must route
  through it — a new raw `<` on `occurred_at` is a bug, and should be treated as one.

## Follow-on gap (logged, NOT fixed here)

**Timestamp canonicalization belongs at the INGESTION BOUNDARY, not only at compare time.**
Immune Stage 1 (or the ingestion path) should validate and canonicalize timezone-bearing
timestamps on the way in, so the system does not rely on compare-time normalization
forever. Today a naive timestamp passes Stage 1 (`datetime.fromisoformat` accepts it) and
is only rejected later, deep in the fold — a boundary failure surfacing as a projection
failure. Every future comparison site is also an opportunity to forget `_instant()`;
a canonicalizing boundary removes the whole class rather than defending each site.

Out of scope for this fix, logged while visible. See also decisions/0004's open gaps.

## Alternatives considered

- **Canonicalize `occurred_at` to UTC at write time and keep string comparison.**
  Rejected: `occurred_at` is inside the hashed envelope. Rewriting it changes every
  `event_hash`, breaks the chain, and breaks replay determinism (§6). If timestamps are
  ever canonicalized at rest, it must happen at the boundary *before* hashing — which is
  the follow-on gap above, not a comparison fix.
- **Assume naive timestamps are UTC.** Rejected: a silent assumption about an ambiguous
  instant, which is the failure mode this ADR exists to eliminate. Fail loud instead.
- **Fix only the guard in `fold`.** Rejected outright: `assert_not_backdated` performs the
  same comparison, and a half-fixed guard is arguably worse than an unfixed one — the two
  sites would disagree about which events are backdated.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
