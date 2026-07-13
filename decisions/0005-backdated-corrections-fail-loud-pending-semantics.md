# 0005 — Backdated corrections fail loud (interim), pending a decision on their semantics

- **Status:** Accepted as an **INTERIM STANCE** — ratified by Josh, 2026-07-13.
  This ADR does **not** decide what a backdated correction *means*. It decides only
  that we refuse to guess, and refuse *audibly*, until someone does.
- **Date:** 2026-07-13
- **Scope:** `src/nyx/projection.py` (`BackdatedCorrectionError`, `assert_not_backdated`),
  `src/nyx/skeleton.py` (pre-append check), `tests/test_correction_appended.py`
- **Relates to:** Invariants 1, 8 · V0 §1 (value-recency guard), §6 (replay), §7 (gap
  protocol, case 3), §8 · [decisions/0004](0004-correction-appended-supersedes-via-superseding-events.md)

## Context

ADR 0004 built the `correction_appended` handler for the case the spec actually
describes: a correction carrying a **later** `occurred_at` than the value it corrects.
It flagged the inverse case as an open gap — a **backdated** correction, whose
`occurred_at` *predates* the value it corrects.

Left alone, that case does not crash. It flows through the §1 value-recency guard and
folds as **provenance only**: the correction is accepted, appended, added to the support
set — and the belief head *does not move*. The system reports success and changes
nothing. That is the dangerous shape of failure: not an error, but a **plausible-looking
wrong answer**, arrived at by an unexamined default that the next reader would very
reasonably mistake for a decision.

## The question this defers — and it stays open

Is a correction **newer information**, or an **authoritative override**?

- **(A) Recency-governed.** A correction is a value-setting event like any other, and §8
  says plainly that "the value-recency guard applies to all value-setting handlers."
  Under (A) a backdated correction is simply an old datum arriving late — the
  reconnection seam (§5 trace 2) — and correctly folds as provenance only. The head
  stays put.
- **(B) Authoritative override.** A correction is not an observation; it is a deliberate,
  authoritative act — *"no, it was always 128GB, the sensor was misreading."* Its
  `occurred_at` describes **when the corrected fact held**, not when the knowledge
  arrived. Under (B) a backdated correction **takes the head regardless of its date**,
  because that is the entire point of correcting something.

Both are defensible. (A) has the letter of §8 behind it; (B) has the ordinary meaning of
the word *correction*. The spec settles neither — V0 §1 line 44's whole mechanical
statement is "`correction_appended` supersedes," and §8 line 287 lists the handler as
unworked. **This ADR does not choose.** Choosing would require deciding what
`occurred_at` *means on a correction* (event time vs. validity time), which is a
modelling question with consequences well beyond this handler.

## Decision (interim)

Refuse the case, loudly and specifically.

- A dedicated, greppable error type: **`BackdatedCorrectionError`**, subclassing
  `NotImplementedError` — not a bare `Exception`, not a generic message. It is the §7
  gap protocol's *"stub that fails loudly"*, not a validation error about bad input.
  Its docstring carries the A-vs-B question, so the open question travels with the code
  rather than living only here.
- One predicate, `assert_not_backdated(prior_view, event_type, occurred_at)`, called from
  **two** places (see below).
- A test asserting the raise, so the stance is pinned and its removal is deliberate.

**When the semantics are decided, `BackdatedCorrectionError` greps straight to every site
that assumed the question was open** — the raise, the pre-append check, the test. That is
the point of naming it: the interim stance is designed to be *found and deleted*, not to
harden into permanence by being invisible.

## Why the check runs BEFORE the append, not at fold time

This is the load-bearing mechanical detail, and it is not a style choice.

The write path appends to Layer A and *then* folds. Layer A is append-only and
**engine-enforced** (Invariant 1: UPDATE/DELETE triggers), and the append **is** the
durable commit point (Invariant 8). So a backdated correction that were appended first
and rejected at fold time afterwards would be **permanently in the log** — unremovable by
construction. Every subsequent full replay would re-fold it and raise. The log would
become unreplayable, and replay is the crash-recovery path *and* the determinism oracle
(§6). An unreplayable log is an unrecoverable one.

Hence: the rejection happens **before the commit point, while rejecting is still
possible**. `fold` also calls the predicate, as the replay-side backstop — but that call
can only ever fire on a log that should not exist. `tests/test_correction_appended.py::
test_backdated_correction_does_not_poison_layer_a` pins exactly this: after the raise,
`events` still holds one row, the belief is untouched, and the log still replays.

## Consequences

- 13 tests green.
- A backdated correction is currently **unsupported**, not "handled." Callers get a loud,
  named failure. No caller may treat the raise as the semantics — it is the *absence* of
  semantics.
- ADR 0004's open gap #1 is now **enforced** rather than merely documented: the wrong
  answer is no longer reachable by accident.
- This ADR is expected to be **superseded**, not amended. Whoever decides A-vs-B writes
  0006 and deletes the raise, the predicate's call sites, and the test in one change.

## Alternatives considered

- **Leave it to the value-recency guard (i.e. silently implement (A)).** Rejected: it
  fails *quietly*. The correction is accepted and the head silently does not move — and
  the next reader cannot distinguish "we chose (A)" from "nobody looked." Under CLAUDE.md's
  gap protocol this is precisely the outcome to avoid: *"do not design a silent solution
  that reads as a real decision to the next reader."*
- **Implement (B) now — correction always takes the head.** Rejected: it is the *plausible*
  answer, which is exactly why guessing is dangerous. It contradicts §8's "the guard
  applies to all value-setting handlers," and it silently redefines `occurred_at` on a
  correction from event time to validity time — a modelling change no spec document makes.
- **Raise a generic `ValueError` / bare `Exception`.** Rejected: the interim stance must be
  trivially findable and trivially deletable. A generic error buries it.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
