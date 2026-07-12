# 0003 — Genesis sentinels and hash-material delimiters

- **Status:** Accepted — 2026-07-12
- **Date:** 2026-07-12
- **Scope:** Walking skeleton (commit two), `src/nyx/hashing.py`,
  `src/nyx/projection.py`
- **Relates to:** Invariant 9 (projection determinism) · V0 §1 (deterministic
  algorithms) · Architecture §12 (fold ≡ replay executable invariant)

## Context

Three hash inputs in V0 §1 are specified by their *formula* but leave a byte-level
detail unstated. Because `event_hash` and `view_version_hash` must reproduce
byte-for-byte across machines (`fold ≡ replay-from-genesis`, Architecture §12),
these details are load-bearing and must be pinned once, explicitly, rather than
chosen ad hoc at each call site.

The three:

1. **Chain genesis.** `event_hash = SHA256(canonical_json(env) || prev_event_hash)`.
   The first event has no predecessor (`prev_event_hash` is NULL in the schema).
   What does the `|| prev_event_hash` term contribute at genesis?
2. **View-hash genesis.** `view_version_hash = SHA256(prior_view.view_version_hash
   || new_event.event_hash)`. The first event to touch a belief has no prior view.
   What is the seed?
3. **Concatenation ambiguity.** `idempotency_key = SHA256(source_id || occurred_at
   || canonicalize(payload))`. Bare concatenation lets `("ab","c")` and `("a","bc")`
   collide.

## Decision

1. **Genesis `prev_event_hash` contributes the empty string.** `hashing.event_hash`
   coerces a `None`/missing prev hash to `""`. The stored column stays `NULL`; only
   the hash *input* uses `""`.
2. **Genesis view seed is the empty string.** `projection._GENESIS_VIEW_HASH = ""`;
   the first fold for a belief hashes `"" + event_hash`.
3. **Hash material is joined with a fixed unit separator (`\x1f`).**
   `hashing._SEP = "\x1f"` joins the three idempotency components, so distinct field
   boundaries cannot collide.

## Rationale

- The empty string is the conventional, minimal genesis sentinel; it makes the first
  link a pure function of the first envelope, and every subsequent link a pure
  function of `(prior, current)`. Determinism (Inv. 9) holds from the first event.
- Keeping the stored `prev_event_hash` as `NULL` while using `""` only in the hash
  input preserves the schema's honest "there was no predecessor" while giving the
  hash a well-defined input. The two are not in tension.
- `\x1f` (ASCII Unit Separator) is non-printable and will not occur in a `source_id`,
  ISO-8601 timestamp, or canonical JSON, so it is an unambiguous delimiter. This is a
  strict improvement on the spec's `||` (which is conceptual concatenation, not a
  byte-level spec) and is **internal-only** — the idempotency key is used for dedup
  within a single database, never as a cross-implementation contract, so pinning the
  separator here is safe.

## Consequences

- These three constants are now part of the hash contract. Changing any of them
  changes every downstream hash and breaks replay equivalence against existing data —
  so a change is a migration, not a tweak, and would need its own ADR + a
  `schema_version` / projector-version bump.
- The same discipline (one canonical hashing utility, `hashing.py`) already unifies
  the Liver dependency hash and the process-trace hypothesis hash (V0 §1/§13); these
  sentinels live in that one utility, not scattered per call site.

## Alternatives considered

- **A zero-hash (64 `"0"` chars) genesis sentinel.** Common in blockchains; rejected
  as heavier than needed and no more deterministic than `""` for a local log.
- **Bare concatenation for the idempotency key (spec-literal).** Rejected for the
  collision risk above; the cost of a delimiter is nil and the correctness gain real.
- **Length-prefixing each field instead of a delimiter.** Equivalent correctness,
  more code; the separator is simpler and sufficient given `\x1f` cannot appear in
  the inputs.

---

*Supersede with a new file if the hash contract ever changes; never edit a ratified
hash-contract ADR in place — the whole point is that these bytes are fixed.*
