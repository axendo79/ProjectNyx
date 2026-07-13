# 0007 — `payloads` is keyed by `event_id`, not `payload_hash` (§4's DDL is the bug)

- **Status:** Accepted — ratified by Josh, 2026-07-13
- **Date:** 2026-07-13
- **Scope:** `schema.sql` (`payloads` table + `idx_payloads_corroboration`),
  `src/nyx/storage.py` (`safe_append_event`),
  `tests/test_corroboration_payload_identity.py`
- **Relates to:** Invariant 14 (erasure boundary) · V0 §2 (minimum sample floor /
  corroboration gate), §4 (schema — **the document that is wrong**), §8

## Context

`NYX_V0_IMPLEMENTATION.md` §4 specifies:

```
CREATE TABLE payloads (
    payload_hash    TEXT PRIMARY KEY,
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    ...
```

`schema.sql` transcribed that faithfully. It is wrong, and the table is internally
contradictory on its face: it carries **`event_id`** (one row per EVENT — 1:1) while being
**keyed by content** (one row per distinct payload — n:1). Both cannot hold. The moment two
events share payload content, the primary key decides the question by rejecting the second
event.

Since `payload_hash = SHA256(canonical_json({belief_id, value, verifiability}))`, two events
share content exactly when two sources report **the same value for the same belief**.

## The two independent reasons content-keying is wrong

**1. It blocks corroboration — the only v0 promotion path.**

V0 §2 sets the gate:

> *"Minimum sample floor (corroboration gate, §2/§4). v0: **2** independent corroborating
> sources required for `unverified -> verified` via corroboration."*

Two independent sources reporting the same value **is** corroboration. It is also, exactly,
the case that produces identical payloads and collides on the PK. So the schema cannot
store the second corroborating source, and **the corroboration gate is unreachable by
construction.** The sole promotion path in v0 was dead in the DDL. This is not a constraint
annoyance; it is a foundational capability that could never have worked.

Demonstrated red before the fix:
`sqlite3.IntegrityError: UNIQUE constraint failed: payloads.payload_hash`, on all three
tests in `tests/test_corroboration_payload_identity.py`.

**2. It pools payloads across events — an Invariant 14 violation.**

Invariant 14 makes payloads **separately destroyable per event** by crypto-shredding
(destroy the key, not the bytes). Under content-keying, two events *share a single payload
row*. Redacting one event would therefore destroy the **other** event's payload as
collateral — silent erasure of a record nobody asked to erase, and an un-auditable one.

This reason is independent of corroboration and would condemn the content-keyed PK on its
own. Two independent invariant failures converging on one line of DDL is what makes this a
design error rather than an oversight.

## Decision

- **`event_id` is the PRIMARY KEY.** It is the identity the table always implied by carrying
  the column at all.
- **`payload_hash` remains, NOT NULL and non-unique** — content-addressing is intact.
  Identical claim content still yields an identical hash; the hash simply stops being the
  row's *identity*.
- **Per the two-file provenance rule, V0 §4 is authoritative for schema — so V0 §4 is the
  bug.** This is a deliberate deviation from the authoritative document, recorded rather
  than silently repaired (CLAUDE.md: *"If something looks wrong, flag it and ask. Do not
  quietly change it."*). §4's DDL should be corrected to match this file.

## The index has a job — it is the corroboration lookup key

`idx_payloads_corroboration ON payloads(payload_hash)` is **not** a generic content-lookup
afterthought. It is the key the §2 corroboration gate will stand on. The question that gate
must answer is *"which other events assert this same claim?"*:

```sql
SELECT e.event_id, e.source_class FROM payloads p
  JOIN events e ON e.event_id = p.event_id
 WHERE p.payload_hash = ?
```

...from which the gate counts **DISTINCT `source_class`** — not raw events. §2 is explicit
that corroboration counts distinct classes precisely so correlated ingestion (shared model
context, re-entrant synthesis, a duplicate pasted origin) cannot self-corroborate.

The index is **deliberately non-unique**: n events per content is the entire point, and the
uniqueness of that column is what was broken.

**The gate itself is not built** (§8). This ADR builds the lookup it will require, and says
so, rather than leaving the index's purpose to be inferred later.

## Consequences

- 19 tests green (3 new + the existing 16, none regressed).
- `safe_append_event` inserts payloads keyed by `event_id`, with **no conflict clause**,
  deliberately: the `INSERT OR IGNORE` on `events` already returns `False` on a duplicate
  `idempotency_key`, so the payload insert is reached only for a freshly-appended event,
  whose `event_id` is new by construction. A PK violation there would mean a **reused
  `event_id`** — a real bug that must fail loudly, not be absorbed by an `ON CONFLICT`.
- **No migration is required.** No database is tracked in git, none exists in the repo root,
  `*.db`/`*.sqlite*` are gitignored, and every test builds a fresh database in `tmp_path`.
  The only databases that have ever existed are per-test temporaries.
- Content-identical payloads are now stored once per event, so the same ciphertext may
  appear in more than one row. That is correct: they are separately destroyable records
  that happen to say the same thing, and conflating them is what Invariant 14 forbids.

## Follow-on gap (logged, NOT fixed here)

**There is no schema migration path, and no schema versioning.** `storage.init_db` applies
`schema.sql` only when the `events` table is *absent*. A pre-existing database therefore
keeps its old DDL silently — it is neither migrated nor rejected. Harmless today (no
persistent database exists), and a real trap the first time one is long-lived: this very
change would have left such a database on the old content-keyed PK, still unable to
corroborate, with nothing to announce it. A schema-version check in `init_db` that refuses
or migrates a mismatched database belongs on the list before any database outlives a test
run.

## Alternatives considered

- **Composite PK `(payload_hash, event_id)`.** Rejected: it permits both rows, so it unblocks
  corroboration — but it leaves `payload_hash` looking like a shared identity and does nothing
  to clarify that erasure is per-event. `event_id` alone states the 1:1 truth plainly.
- **Deduplicate: one payload row, many events pointing at it.** Rejected outright — this is
  reason 2 above, made into a design. It is exactly the Invariant 14 collateral-erasure
  failure, and it would also require a reference-counting scheme to know when shredding a key
  is safe. Storage savings are not worth a silent erasure bug.
- **Keep the §4 DDL and work around it** (e.g. salt the payload so hashes differ). Rejected:
  it would break content-addressing to preserve a broken key, and disguise a spec bug as an
  implementation quirk.

---

*Decision-log format: one decision per file, `NNNN-kebab-title.md`, append-only in
spirit — supersede with a new file rather than rewriting a ratified one. Style per
`NYX_V0_IMPLEMENTATION.md` §8.*
