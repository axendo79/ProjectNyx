# CLAUDE.md — Nyx build guidance

## The one rule that overrides everything

**The spec is complete. Build it, don't redesign it.** The three documents in
`spec/` (`NYX_ARCHITECTURE.md`, `NYX_V0_IMPLEMENTATION.md`, `NYX_COUNCIL.md`) are
the finished, adversarially-hardened build spec. Your job is to *execute* them.

- Do **not** silently "improve" the architecture, schema, or a v0 default. If
  something looks wrong, **flag it and ask** — surface it in your response (or a
  decision-log entry). Do not quietly change it.
- Additional spec-review passes are **avoidance, not progress** (see
  `spec/HANDOFF_2026-07-11.md`). The blocker was never design; it was *starting*.
  The gating milestone is a **running walking skeleton**, not a more-reviewed spec.
- On any conflict between spec files, **the more specific mechanical statement
  wins** (two-file provenance rule). `NYX_ARCHITECTURE.md` is authoritative for
  *what/why*; `NYX_V0_IMPLEMENTATION.md` is authoritative for *how* (schema,
  algorithms, defaults, tests). The other file is then the bug — not a second
  opinion to reconcile in prose.

Read `spec/HANDOFF_2026-07-11.md` first — it explains why this is a fresh repo
(the old `nyx-core-v2` flat-JSONL design is *superseded*, not being ported).

## The Constitution — 15 invariants no component may violate

Full text: `spec/NYX_ARCHITECTURE.md` §Constitution. Condensed, so a change can
be checked against them without a reread:

1. **Append-only Reality.** Layer A is append-only, engine-enforced (SQLite
   trigger). Synthesis never mutates it. Correction supersedes, never edits.
2. **Confidence is never Evidence.** Evidence creates confidence; confidence
   never creates evidence. Never render fake-precise confidence.
3. **No Silent Promotion.** Nothing moves toward VERIFIED without an independent
   signal. Demotion may fire on internal consistency; promotion may not.
4. **Verification Domain Separation.** Three oracle classes: *world oracle*
   (only class that may promote world-truth), *derivation validator* (validates
   synthesis, demotes/grades, cannot promote), *structural auditor* (demotes,
   cannot grade). Re-derivation from Layer A is not world evidence.
5. **Origin is Immutable.** Every event carries an immutable origin type. A
   derived statement becomes a fact only by a *new* event, never by mutation.
6. **Support-Set Provenance.** A resolved belief exposes its supporting/opposing/
   superseding/gap events. Verification adds to the set, never rewrites a member.
7. **Reason Freely, Remember Conservatively.** Reasoning is ephemeral; memory is
   durable by exception. Nothing enters Layer A unless an oracle exception fires.
8. **Commit-Point Sovereignty.** A Layer A append is the only durable commit.
   No derived artifact (view, queue, index, cache) is the sole copy of anything.
9. **Projection Determinism.** Resolved View = `project(log, as_of, version)`.
   Conflict resolution, decay, tie-breaks are deterministic, time-aware, versioned.
10. **Behavioral Invariance.** Equivalent evidence → equivalent epistemic
    outcome. Tone/framing/identity/urgency are presentation, never epistemic.
11. **Affective Invariance.** Detected emotion (and self-referential
    `meta_commentary`) influences *style only*, never epistemic state. Enforced
    structurally: extraction sees only semantic payload; affect travels parallel.
12. **Proportional Governance.** Governance depth scales with stakes; the full
    apparatus is exception machinery, not default machinery (cost tiers, §6).
13. **User Tags are Hints, not Gates.** An ingest classification alters the
    *initial* annotation and queue priority; it never bypasses checks.
14. **Erasure Boundary — envelope/payload split.** Hash chain covers envelopes
    only; payloads are separately destroyable by crypto-shredding (destroy the
    key, not the bytes). Erasure is oracle-gated; Layer B may propose, not execute.
15. **Retroactive Reinterpretation Never Promotes.** Redaction, entity merge/
    split, re-resolution may demote or hold — never directly promote. A would-be
    promotion re-earns its state through the normal gated path.

## Build order (do not get ahead of this)

- **Commit 1 — scaffold only, no logic. [DONE — this baseline]** spec/, schema,
  CLAUDE.md, `.gitignore`, `.gitattributes` (LF/hash-determinism), typed module
  stubs (`NotImplementedError` bodies), empty `tests/`. Known-good green baseline.
- **Commit 2 — the walking skeleton (`NYX_V0_IMPLEMENTATION.md` §6). TEST-FIRST.**
  Write the test first: one inline `observation_recorded` event → immune Stage 1
  only → append to Layer A (idempotency + hash chain) → delta-reducer fold into
  `resolved_beliefs` → read back → **full-replay hash matches**. Acceptance bar
  is the GIVEN/WHEN/THEN block in §6. Nothing else in this commit — no file
  ingestion, no corpus, no immune Stages 2–4. Just the one event through the seam.
- **Later:** Phase 1 breadth, then Phases 2–3 (`NYX_ARCHITECTURE.md` §12). The
  five pre-coding seam traces (`NYX_V0_IMPLEMENTATION.md` §5) become permanent
  property-based tests: assert `fold ≡ replay-from-genesis`, support graph stays
  a DAG, no state transition promotes as a side effect of redaction/merge.

## Gap protocol — which of four cases are you in? (`NYX_V0_IMPLEMENTATION.md` §7)

Before proceeding or stopping at any underspecified point, identify the case:

1. **Operational v0 default (§2) — SETTLED.** Code against it directly. Do not
   ask, do not silently "improve" it. Add a comment citing its retune trigger.
2. **Explicitly deferred (§3) — DO NOT invent a substitute.** Use the stated
   fallback (state + support set stand in for a confidence score; if a number is
   truly needed, it's the corroboration *count*, never a synthesized float).
   Comment why nothing exists here, pointing at §3.
3. **Still open / unworked (§8) — STOP.** Write a stub that fails loudly
   (`raise NotImplementedError("... see NYX_V0_IMPLEMENTATION.md §8")`) or ask.
   Do not design a silent solution that reads as a real decision to the next reader.
4. **Not in either document at all — highest-priority STOP.** Zero guidance means
   zero grounds to guess. Ask.

## Hash determinism (why `.gitattributes` forces LF)

`event_hash` and `view_version_hash` must be byte-for-byte reproducible across
machines (`fold ≡ replay-from-genesis` is an executable invariant,
`NYX_ARCHITECTURE.md` §12). A CRLF/LF difference in any hashed file or golden
fixture breaks replay. `.gitattributes` pins LF repo-wide; do not weaken it.
Canonical JSON (sorted keys, fixed float format, no whitespace variance) is the
same discipline at the data layer (`NYX_V0_IMPLEMENTATION.md` §1).

## Environment

- Target: `D:\ProjectNyx`, Git Bash on Windows, branch `main`.
- Remote: `https://github.com/axendo79/ProjectNyx.git` (auth via Windows
  Credential Manager). Public repo — Code owns the first commit.
- Python 3.14 (target ratified in decisions/0009; this re-adopts the version the
  runtime has been on all along and supersedes the handoff's 3.14→3.11/3.12 P0).
