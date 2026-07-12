# 0002 — Payloads are stored as plaintext in v0; at-rest encryption is Phase 3

- **Status:** Accepted — 2026-07-12
- **Date:** 2026-07-12
- **Scope:** Walking skeleton (commit two), `src/nyx/events.py` `build_event()`,
  `payloads.ciphertext` column
- **Relates to:** Invariant 14 · Architecture §12 (phasing), §5 (erasure) · V0 §4, §8

## Context

The `payloads` table (V0 §4) names its content column `ciphertext` because the
target design encrypts each payload at write with a per-canonical-entity key and
performs erasure by **crypto-shredding** — destroying the key, not the bytes
(Invariant 14). The walking skeleton (§6) needs to store and read back the payload
content (`"64GB"`) to fold a belief, but it does **not** need — and must not fake —
the keystore, key binding, or encryption machinery.

Architecture §12 places erasure / crypto-shredding in **Phase 3**; the skeleton is
Phase 1. Immune Stages 2–4 and the keystore are explicitly open/deferred (§8).

## Decision

In v0, `build_event()` writes the payload as **plaintext canonical JSON** into the
`ciphertext` column (`redacted = 0`). No encryption, no keystore, no key binding.
The column name is retained as the eventual home for the real ciphertext.

## Rationale

- The skeleton's job is the append→fold→read→verify seam, not erasure. Building a
  keystore now would be implementing a Phase 3 subsystem to satisfy a Phase 1 test —
  exactly the "debugging two systems at once" failure the handoff warns against.
- Faking encryption (e.g. a hardcoded key, or base64 dressed up as ciphertext) would
  be *worse* than plaintext: it would read as a real security boundary to the next
  reader while providing none. Plaintext-with-a-comment is honest about what exists.
- The envelope/payload split (Inv. 14) is already structurally present in the schema
  and the hash chain (the chain covers envelopes only). So adopting real
  crypto-shredding later does **not** require reworking the seam — only populating
  `ciphertext` with actual ciphertext and wiring the keystore.

## Consequences

- **No confidentiality at rest in v0.** Databases hold readable payloads. Acceptable
  for a local single-user substrate that isn't ingesting sensitive material yet; it
  is a real gap the moment it does, and must be closed before any PII/credential
  corpus is ingested.
- `redacted` stays `0`; the typed `REDACTED` replay sentinel (§5) is not yet
  exercised (there are no redactions in the skeleton).
- When Phase 3 lands: encrypt on write against the `canonical_entity_id`-bound key,
  and erasure destroys the key. The `event_hash` is unaffected (chain covers
  envelopes only), so historical chain verification survives key destruction —
  which is the whole point of Invariant 14.

## Alternatives considered

- **Leave `ciphertext` NULL and store the value elsewhere.** Rejected: the fold
  needs the value, and NULL `ciphertext` is reserved to mean *redacted* (§4) — using
  it for "not yet encrypted" would collide with that meaning.
- **Build a minimal keystore now.** Rejected: Phase 3 work pulled into Phase 1, and
  the erasure mechanism per data class is still an open TBD (Architecture §13).

---

*Supersede this ADR (new file) when at-rest encryption lands, rather than editing it.*
