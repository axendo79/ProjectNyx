# Known gaps

Open findings that are **logged, not fixed**. Each is real and verified against the code —
not a suspicion. None has a silent workaround in place; where the code would otherwise
produce a plausible-looking wrong answer, it fails loudly instead.

This file is the register. Where a gap carries enough reasoning that it must not be
relitigated, it has an ADR in `decisions/` and this file points at it.

> **Read [ADR 0008](decisions/0008-fold-signature-cannot-express-cross-belief-events.md)
> before starting any entity-merge work.** It is a fold-seam redesign, not a new handler,
> and it is the one gap here that changes what you are building rather than adding to it.

---

## BLOCKER — read before Phase 2

### The `fold` signature cannot express a cross-belief event
**→ [ADR 0008](decisions/0008-fold-signature-cannot-express-cross-belief-events.md)** ·
Phase 2 blocker · `src/nyx/projection.py`

`fold(prior_view, envelope, payload) -> dict` takes **one** belief and returns **one**
belief; `project` keys every event to exactly one `belief_id`. `entity_merge_accepted`
(and `entity_split_asserted`, and a redaction sweep) affect **many beliefs at once** —
there is nowhere in this signature to put the answer.

This is **a redesign, not an additive branch.** The return type must widen, every caller
changes, and `view_version_hash` — which chains **per belief** (§1) — is entangled with the
change: a single merge event contributes to N belief chains at once, and each possible
answer is a different hash lineage that must still satisfy `fold == replay-from-genesis`
(§12). **The hash design and the fold signature are one decision, not two.** On top of that
sits §5 trace 4 (merge-pooling), whose Invariant 15 rule — pooled evidence crossing a
threshold must land at *hold-plus-gated-proposal*, never automatic promotion — requires a
fold that can see both beliefs at once to evaluate at all.

Budget for the seam. Do not bodge around it; ADR 0008 lists the two tempting bodges and why
both break `fold == replay`.

---

## Correctness gaps

### Redaction breaks the write path and replay
`src/nyx/storage.py` · Invariant 14 · unbuilt, **will fail loudly if reached**

A redacted payload has `ciphertext = NULL` (key destroyed). Two sites assume it is present:

- `safe_append_event` extracts the entity key with `json.loads(payload.ciphertext)["belief_id"]`
  → `TypeError` on `None`.
- `read_all_events` yields a `None` payload for a redacted row, which `project` then
  subscripts → `TypeError`.

So the moment redaction exists, **replay of a log containing a redacted event dies** — and
replay is the crash-recovery path *and* the determinism oracle (§6). The spec's own answer
is that replay must yield a **typed REDACTED sentinel** rather than a broken chain
(`schema.sql`, V0 §4); that sentinel does not exist yet. Redaction is unbuilt, so this is
unreachable today.

### `project()` assumes every event is belief-scoped
`src/nyx/projection.py` · **will fail loudly if reached**

```python
belief_id = payload["belief_id"]   # every event, no exceptions
```

Any event whose payload has no `belief_id` — `entity_merge_accepted`, `redaction_applied`,
`gap_recorded` — raises `KeyError`. Today only value-setting events exist, so it holds.
It stops holding at the first non-belief-scoped event type. Related to ADR 0008 but
distinct: this one is a missing *dispatch*, that one is a missing *shape*.

### `as_of` / `projector_version` are accepted and ignored
`src/nyx/projection.py` · **Invariant 9** · silent

```python
def project(events, as_of, projector_version):   # neither parameter is ever read
```

Invariant 9 requires `Resolved View = project(log, as_of, version)` — deterministic,
**time-aware**, versioned. The signature advertises exactly that. The body honours none of
it: `as_of` does not bound which events are folded, and `projector_version` selects nothing.

**This is the most deceptive gap in the list**, and the reason it is written down rather
than left to be noticed: the other gaps announce themselves with an exception. This one
looks implemented. A caller passing a historical `as_of` gets a confident answer computed
from the *entire* log, including events after that instant — a plausible-looking wrong
answer, which is the failure mode this project exists to refuse. Nothing depends on it yet
(every caller passes a value that happens to be current), which is exactly why it can rot
undetected.

---

## Schema / operational gaps

### No schema migration path, and no schema versioning
`src/nyx/storage.py` (`init_db`) · **fix before any database outlives a test run** ·
found while landing [ADR 0007](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md)

`init_db` applies `schema.sql` only when the `events` table is **absent**. A pre-existing
database therefore keeps its old DDL silently — it is neither migrated nor rejected.

The concrete case is not hypothetical: **ADR 0007 changed the `payloads` primary key.** Had
any persistent database existed, it would still be running the old content-keyed PK — still
unable to corroborate, with nothing whatsoever announcing the mismatch. Harmless today
(every database is an ephemeral `tmp_path` fixture), and a landmine the moment ingestion
starts persisting a real corpus.

Minimum fix: a schema-version row, checked on open, that **refuses** a mismatched database
rather than proceeding against it.

### Timestamp canonicalization belongs at the ingestion boundary
`src/nyx/immune.py` · follow-on from
[ADR 0006](decisions/0006-occurred-at-comparison-is-instant-based-not-lexical.md)

`occurred_at` ordering is now instant-based at both comparison sites, but nothing
canonicalizes timestamps on the way *in*. A naive (offset-less) timestamp passes immune
Stage 1 (`datetime.fromisoformat` accepts it) and is only rejected later, deep in the fold —
a boundary failure surfacing as a projection failure. Every future comparison site is also a
chance to forget `_instant()`. A canonicalizing boundary removes the class instead of
defending each site one at a time.

---

## Undecided semantics (fail loud, on purpose)

### Backdated corrections
**→ [ADR 0005](decisions/0005-backdated-corrections-fail-loud-pending-semantics.md)** ·
raises `BackdatedCorrectionError`

A correction whose `occurred_at` predates the value it corrects is **refused**, pending a
decision: is a correction *newer information* (recency-governed → folds as provenance only)
or an *authoritative override* (takes the head regardless of date)? Settling it means
settling whether `occurred_at` on a correction is **event** time or **validity** time. The
raise is greppable so the decision, when made, finds every site that assumed it was open.

### Origin → verification_state beyond `observed`
**→ [ADR 0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md)** ·
`_state_for_origin` raises `NotImplementedError`

Only `observed` is mapped (ADR 0001). `user_stated` cannot reuse it: architecture §2's
user-stated split ("User asserted X" vs "X is true" — the user is a *source*, not ground
truth, outside preference claims) means it must earn its state differently.

---

## Noted, not acted on

- **`idempotency_key` omits `event_type`.** V0 §1 defines it as
  `SHA256(source_id || occurred_at || canonicalize(payload))`. An observation and a
  correction with identical source, time, and payload would collide into one row. §1 is
  explicit, so this was not changed — recorded as a latent edge. ([ADR 0004](decisions/0004-correction-appended-supersedes-via-superseding-events.md))
- **Python version.** Runtime is **3.14.2**; `CLAUDE.md` says 3.11/3.12 ("the spec's earlier
  3.14 target was walked back"). Suite is green on 3.14. One of the two is stale.
- **`gap_events` has no column.** Invariant 6 names four event classes a belief exposes
  (supporting, opposing, superseding, gap); `resolved_beliefs` now carries three. No
  `gap_recorded` handler exists yet, so this is an absence, not a decision.
- **V0 §4's DDL is wrong about the `payloads` primary key.** Corrected in `schema.sql` per
  [ADR 0007](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md); the spec file
  itself still needs fixing.
