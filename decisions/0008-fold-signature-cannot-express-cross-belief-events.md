> **Resolved 2026-09-08:** [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md) supersedes this recorded blocker by deciding reducer shape and hash lineage together. The original finding below is retained as historical context. Implementation is separate; ADR 0014 explicitly refuses merges with differing predecessor verification states pending a further decision.

# 0008 — The `fold` signature structurally cannot express a cross-belief event (Phase 2 blocker)

- **Status:** Superseded by ADR 0014 (accepted 2026-09-08). Recorded blocker resolved;
  implementation pending.
- **Date:** 2026-07-13
- **Severity:** **Phase 2 blocker.** Must be seen BEFORE entity-merge work starts —
  not discovered halfway through it.
- **Scope:** `src/nyx/projection.py` (`fold`, `project`) — the fold seam itself
- **Relates to:** Invariants 6, 9, 15 · V0 §1 (fold algorithm, `view_version_hash`),
  §5 trace 4 (merge-pooling), §8 (`entity_merge_accepted` unworked) ·
  Architecture §12 (`fold == replay` executable invariant)

## The finding

```python
def fold(prior_view: dict | None, envelope: Envelope, payload: dict) -> dict:   # ONE belief in, ONE belief out
def project(events, as_of, projector_version) -> dict[str, Any]:
    for envelope, payload in events:
        belief_id = payload["belief_id"]                                        # ONE belief per event
        view[belief_id] = fold(view.get(belief_id), envelope, payload)
```

The fold takes **one prior belief view** and returns **one belief view**. `project` keys
every event to **exactly one `belief_id`**. The signature encodes an assumption that has
so far been true and will not stay true: *every event affects exactly one belief.*

**`entity_merge_accepted` affects many beliefs at once, by definition.** So does
`entity_split_asserted`. So does a redaction sweep. None of them can be expressed in this
signature — not because a branch is missing, but because **there is nowhere to put the
answer**. A merge's result is a *set* of belief transitions, and `fold` has a return type
that can hold one.

## Why this is a redesign, not an additive branch

This is the distinction that matters, and the reason this is recorded prominently instead
of as a bullet in a gaps list.

Every event handler so far — `observation_recorded` (ADR 0001), `correction_appended`
(ADR 0004) — was an **additive branch**: a new `if` inside a fold whose *shape* already
fit. `entity_merge_accepted` is not that. Making it work means changing what a fold *is*:

1. **The return type must widen** — from one belief to a set of affected beliefs.
   Every caller changes. `project`'s per-belief keying changes.
2. **`view_version_hash` is entangled with the change.** It chains
   `SHA256(prior_view_hash || event_hash)` **per belief** (§1). A single merge event now
   contributes to *N* belief chains at once. Which beliefs' chains does it enter, in what
   order, and does a belief not otherwise touched by the merge still advance its hash?
   Each answer is a different hash lineage — and `fold == replay-from-genesis` (§12, the
   executable invariant) must survive whichever is chosen. **The hash design and the fold
   signature cannot be decided independently.**
3. **§5 trace 4 (merge-pooling) is a correctness trap sitting on top of it.** Two entities
   whose *pooled* events cross a `verified` threshold neither cleared alone must land at
   **hold-plus-gated-proposal, never automatic promotion** (Invariant 15: retroactive
   reinterpretation never promotes). That rule needs a fold that can *see* both beliefs at
   once to even evaluate it — which is precisely what the current signature forbids.

So: attempting `entity_merge_accepted` as "just another handler" will hit the signature
wall immediately, and the natural pressure at that moment is to bodge around it (fold the
merge N times, once per belief; or mutate views outside the fold). **Both bodges break
`fold == replay`** — the first by making the hash chain depend on an ordering nobody
specified, the second by putting state changes outside the only path replay reproduces.

## What this ADR decides

**Nothing.** Deliberately.

It does not propose a signature, a hash scheme, or a merge algorithm. Choosing any of
those requires deciding how `view_version_hash` composes across beliefs — a design question
entangled with Invariant 9 (projection determinism) and Invariant 15 (no promotion via
reinterpretation), which no spec document currently settles.

Its entire purpose is that **whoever opens entity-merge work reads this first**, budgets
for a fold-seam redesign, and does not discover mid-implementation that the seam they are
standing on cannot hold the thing they are building.

## Do not

- Do **not** add `entity_merge_accepted` as an `if` branch in the current `fold`.
- Do **not** widen the return type ad hoc without settling `view_version_hash` composition
  — the hash and the signature are one decision, not two.
- Do **not** work around it by calling `fold` once per affected belief. It reproduces the
  bug with the evidence hidden, and silently makes the hash lineage order-dependent in a
  way §1 never sanctioned.

## Prerequisite before merge work

A decision on **how `view_version_hash` composes for a multi-belief event**, satisfying
`fold == replay-from-genesis` (§12) under Invariant 9. That decision comes first; the
signature follows from it. When it is made, it supersedes this ADR.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
