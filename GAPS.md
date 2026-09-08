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

`fold(prior_view, envelope, payload, as_of) -> dict` takes **one** belief and returns **one**
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

### `as_of` / `projector_version` — resolved
**RESOLVED ([ADR 0010](decisions/0010-projection-parameters.md), commit `101007b`):** `project()` now
bounds `recorded_at` inclusively and selects a versioned fold from a registry;
unsupported versions raise. `fold()` receives an explicit evaluation time for
`projected_as_of`, and `updated_at` comes from the last included event's `recorded_at`.
Regression tests compare complete serialized views across incremental fold and replay at a shared evaluation time, and cover a single-belief live write. They do not establish whole-view equality for live materialized beliefs updated at different times; that finding remains open below.

---

### Whole-view equality across live materialized beliefs and replay
**OPEN - decision required** | `src/nyx/skeleton.py`, `src/nyx/projection.py` | Invariant 9 |
[ADR 0010](decisions/0010-projection-parameters.md)

The live write path passes its call-time evaluation timestamp to `fold()` and updates
only the affected belief. If belief A is updated at T1 and belief B at T2, their
materialized `projected_as_of` values differ. A full `project(log, T2, version)` assigns
T2 to both included beliefs, so the complete materialized mapping and replay result
are not byte-identical. The reproduced difference is in evaluation timestamps;
belief values and hashes matched.

The shared-time incremental/replay tests supply one evaluation time to every fold;
the live-path equality tests cover one belief. Neither resolves the multi-belief case.
The call-time rule and the claimed whole-view equality therefore need an explicit
decision on the equality contract and evaluation-time semantics. No resolution is
ratified here: this finding does not authorize timestamp normalization, relabeling,
a weaker equality assertion, or any behavior change. The cross-belief event-shape
blocker in ADR 0008 remains a separate open issue.

---

## Schema / operational gaps

### Database schema versioning — resolved
**RESOLVED ([ADR 0011](decisions/0011-database-schema-versioning.md)):** `init_db()`
validates metadata on every new connection. Ordinary opens never create or stamp
metadata. Explicit `create=True` initializes only an empty database, with schema
and metadata in one transaction; non-empty creation requests refuse. Missing,
zero, unsupported, or malformed metadata refuses without repair or migration.
The ADR acceptance tests cover refusal without mutation and rollback on failure.
Automatic migrations remain outside scope; incompatible databases are rejected.

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
- ~~**Python version.** Runtime is **3.14.2**; `CLAUDE.md` says 3.11/3.12 ("the spec's earlier
  3.14 target was walked back"). Suite is green on 3.14. One of the two is stale.~~ **RESOLVED
  ([ADR 0009](decisions/0009-python-314-re-adopted-as-target.md)):** 3.14 re-adopted as the
  target. The architecture §402 downgrade P0 was never enforced, 3.14 is the only interpreter
  installed, and the suite is green on it. `CLAUDE.md` and §402 updated to match.
- **`gap_events` has no column.** Invariant 6 names four event classes a belief exposes
  (supporting, opposing, superseding, gap); `resolved_beliefs` now carries three. No
  `gap_recorded` handler exists yet, so this is an absence, not a decision.
- ~~**V0 §4's DDL is wrong about the `payloads` primary key.** Corrected in `schema.sql` per
  [ADR 0007](decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md); the spec file
  itself still needs fixing.~~ **RESOLVED:** §4's DDL now matches `schema.sql`
  (`event_id` PRIMARY KEY, `payload_hash` NOT NULL + corroboration index), with an inline
  note pointing at ADR 0007.
