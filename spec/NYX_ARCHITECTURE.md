# Nyx Architecture

**Status:** The Python/SQLite walking skeleton and stage two under projector "1" are implemented. Broader governance subsystems remain unbuilt; the phase plan in §12 is not a completion checklist. Current stage scope is governed by [ADR 0023](../decisions/0023-stage-two-contract.md). Accepted ADRs supersede this document where they conflict.

**Last update (Sep 11 2026):** Corrected superseded claims and implementation status against accepted ADRs and shipped code. No new decisions. The personality-emergence layer and drift monitor remain unspecified (§13).

**What Nyx is:** an **epistemic kernel** — the protected core that governs what a system believes and how it earns those beliefs. Not a wrapper in the trivial sense, not a full OS. A kernel: it enforces the invariants nothing else may violate, arbitrates finite resources, mediates what becomes knowledge. It governs **belief**, not hardware and not action. An LLM runs *inside* it; agentic/cognitive layers run *on top* as applications, consuming governed beliefs but never reaching past the kernel to corrupt them.

**Epistemic now, cognitive later.** The kernel governs knowing. A planning/action layer that governs *doing* is the goal and sits above as an application. Foundation before roof.

**Governing invariant:** *Nyx never confuses stored text with stored truth, nor stored observation with derived reasoning. Layer A is the closest thing to a local **epistemic ground record** — it preserves what was **asserted**, not what is **true**. All truth claims are provisional, source-bound, and reversible through append-only correction. Derived reasoning is transient unless independently confirmed and recorded as a new event.*

**Document authority:** accepted numbered ADRs in `decisions/` supersede both specifications where they conflict. Subject to those ADRs, this file is authoritative for *what and why* (invariants, component responsibilities, rationale), and NYX_V0_IMPLEMENTATION.md for *how* (schema, deterministic algorithms, defaults, tests). Between the specifications, the more specific mechanical statement wins; it cannot override an accepted ADR.

---

## Constitution (invariants every component obeys)

The architecture grows by **tightening contracts, not adding organs**. Every mechanism below enforces one or more of these; none may violate any.

1. **Append-only Reality.** Layer A is append-only, enforced by the storage engine (§1), not by discipline alone. Synthesis may never mutate it. All change is a new appended event; correction supersedes, never edits.
2. **Confidence is never Evidence.** Evidence creates confidence; confidence never creates evidence. Model confidence is annotation, never a gate (Rule 14). Never render fake-precise confidence.
3. **No Silent Promotion.** No record moves toward VERIFIED without an independent signal. Demotion may fire on internal consistency alone; promotion may not.
4. **Verification Domain Separation.** Verification signals split into three classes with different authority (§5): **world oracle** (human confirmation, direct observation, independent external re-check) — the *only* class that may raise confidence or promote world-truth state; **derivation validator** (re-run a Layer B conclusion from Layer A) — validates *synthesis correctness*, may demote and grade reasoning, **may not** promote world-truth; **structural auditor** (provenance/contradiction/schema check) — may demote, cannot grade. Re-derivation from Layer A is *not* independent evidence about the world.
5. **Origin is Immutable.** Every *event* carries an immutable origin type. A derived statement can never become a stored fact by mutation — only superseded by a *new event* with a different origin.
6. **Support-Set Provenance.** Origin is immutable *on events*. A *resolved belief* has no single mutable origin — it exposes the set of supporting, opposing, superseding, and gap events from which the current value is computed. Verification *adds* to the set, never rewrites a member.
7. **Reason Freely, Remember Conservatively.** Reasoning is ephemeral by default; memory is durable by exception. Nothing enters Layer A unless an **exception** fires — exactly the oracle set — **never** the strength or repetition of the reasoning itself.
8. **Commit-Point Sovereignty.** A Layer A event append is the *only* durable commit. Resolved View, queues, indexes, caches, audit state, and verification debt are reconstructible derivatives. **No derived artifact may be the sole copy** of a fact, correction, obligation, or queue item.
9. **Projection Determinism.** A Resolved View is `project(event_log, as_of_time, projector_version)`. Conflict resolution, decay, entity-link treatment, and tie-breaks must be deterministic, time-aware, and versioned.
10. **Behavioral Invariance.** Equivalent evidence produces equivalent epistemic outcomes regardless of presentation. The messenger's *reliability* is evidence; *tone, framing, identity, verbosity, urgency* are presentation and must not affect epistemic state, confidence, or routing.
11. **Affective Invariance** (special case of 10). Detected emotion may influence interaction style, pacing, clarification frequency, presentation **only** — never epistemic state, confidence, routing, or verification. Enforcement is structural (§1 write path): the claim-extraction step receives *only* the semantic payload; affect metadata travels *parallel*, never through extraction.
    - **Self-referential output is presentation, not evidence (meta_commentary boundary).** Any utterance the system makes *about itself* — a callback to a prior session, an ironic aside, a comment on its own state — is expression riding on real underlying state, and like affect it may never mint a confidence-class value or enter the truth axis. Every such utterance is tagged at generation with `meta_commentary: true` plus a subtype: **`callback`** (references real prior `observation_recorded`/event support — freely allowed, no ceiling; worst case is a bad joke, and the referenced events keep their own truth values, inheriting none to the utterance) or **`self_reference`** (references *inferred* state — an emotion tag that is itself unverified; these compound on an already-soft signal and are the early signal for interiority drift). The tag is descriptive payload, not a judgment, so it needs no oracle gate; it rides the envelope/hash chain for durability like any other event field. Crucially the tag never enters the confidence/ranking axis — a joke about having feelings gets no strength score, exactly as an inferred emotional state gets none. A separate **drift metric** (frequency/escalation of `self_reference`, computed by the personality-emergence monitor as a read-side sweep, *not* a field on the event) rate-limits `self_reference` only; on ceiling-crossing the first implementation **suppresses** the next inferred-state utterance (cleaner to audit under sweep/replay than biasing generation). `callback` is untouched by the ceiling. Same structural move as `source_class` (§2): the discriminator is *which subsystem may read the tag*, not a rule bolted onto one number. *(The broader personality-emergence layer this monitor belongs to is not yet specified — see §13 open item; only the tagging/ceiling mechanism is decided.)*
12. **Proportional Governance.** Governance depth scales with stakes; full apparatus fires only when data is written or stakes are high — made explicit as **cost tiers** (§6): governance is exception machinery, not default machinery. Enforcement is the Budget Manager (§6).
13. **User Tags are Hints, not Gates.** A user's ingest classification alters the *initial* confidence annotation and prioritizes the verification queue. It never bypasses consistency checks or the verification queue.
14. **Erasure Boundary — decided: envelope/payload split.** The constitutional guarantee was never byte-persistence — it's that nothing is *silently* rewritten. Every event is an **envelope** (id, type, occurred_at, actor-as-opaque-id, payload hash, chain hash — PII-free by construction, no free text) plus a **payload** stored separately, content-addressed by that hash. The hash chain covers envelopes only, so a destroyed payload never breaks verification — a verifier can still prove "event N existed, had hash H, and redaction event M (signed, reasoned, timestamped) explains H's absence." Erasure = **crypto-shredding**: payloads encrypted at write with per-canonical-entity keys (bound to `canonical_entity_id` post-resolution, §11 — not `mention_id`, since a key tied to a pre-merge mention has no owner once entities merge or split); erasure destroys the key, not the bytes. Key destruction is a privileged, oracle-gated operation — Layer B may *propose* redaction, never execute it (same spirit as demote-only-offline); credential leaks get a fast-path exception with post-hoc gating.
15. **Retroactive Reinterpretation Never Promotes.** Redaction, entity merge, entity split, and re-resolution are all retroactive reinterpretations of the record. Each may **demote or hold, never directly promote** — a belief that would rise only because supporting evidence was destroyed, or because pooling merged entities crossed a threshold, must route through the normal gated promotion path and re-earn its state from surviving positive evidence. Destruction and reinterpretation are never a write path into higher trust. *(Generalizes what redaction-handling discovered, §5; merges are the mirror case — pooling evidence can auto-promote exactly as destroying counter-evidence can.)*

*Constitution is versioned: `Constitution v1.x`. A law change is a tracked, major event.*

---

## 1. Substrate: storage, projection, write path

The log records *assertions about* reality; it is not reality. Current belief is computed, never stored as fact.

**Layer A — Reality Layer (the event log).** An **append-only `events` table in SQLite (WAL mode)**, append-only enforced by a database trigger blocking `UPDATE`/`DELETE` — a mechanism, not a convention. Stores world-assertion events: observations, claim-assertions, corrections, recorded gaps, entity-resolution *decisions*. Each event: `event_id`, `idempotency_key`, `schema_version`, `event_type`, `occurred_at`, `recorded_at`, `source`, `payload`, `prev_event_hash`/`event_hash` (tamper-evidence via hash chain).

**Layer B — Synthesis / Derived Knowledge.** Dream, reflection, scoring, entity resolution, generated statements. Reads Layer A, never mutates it. Output is derived and, by default, not stored (§2).

**Resolved View — materialized deterministic projection.** **Decided:** the view is **materialized by a deterministic delta-reducer**, not recomputed by full replay on every read (full replay is O(N) and stalls at scale). Each new Layer A event is folded incrementally into the materialized state, which carries a **version hash**; the stale-with-warning read requirement is described in §8. **The recovery-only replay rule is subject to [ADR 0012's explicit whole-view evaluation exception](../decisions/0012-whole-view-equality.md#explicit-whole-view-evaluation-exception).** The projection obeys Invariant 9 — deterministic, versioned, computed `as_of` an explicit time. Per Commit-Point Sovereignty, the materialized view is always rebuildable from Layer A and never the sole copy of anything. Version "1" belief reads implement stale labels; legacy version "0" reads do not yet implement that disclosure.

**Projector "0" ordinary-observation value resolution keys on `occurred_at`, not fold order.** Fold *order* is insertion order (rowid) for hash-chain determinism — but the *value* a belief resolves to must key on `occurred_at`, because the two diverge at the offline-reconnection seam (§5): a backlog event appends at reconnect time (high rowid) carrying an old `occurred_at`, and naive last-fold-wins would let a three-week-old observation override a newer value already materialized. Rule: **a late-arriving observation whose `occurred_at` predates the currently-materialized value updates provenance and the support set but does NOT supersede the newer value.** `as_of` handles historical *queries*; this rule handles *current-value correctness*. This behavior is superseded under projector "1" by [ADR 0024](../decisions/0024-no-authoritative-head.md). Correction behavior is governed by [ADRs 0004](../decisions/0004-correction-appended-supersedes-via-superseding-events.md) and [0005](../decisions/0005-backdated-corrections-fail-loud-pending-semantics.md).

### Write path
This is the target pipeline. The shipped wrappers publish synchronously after the separate append commit; no background worker is started. Rejection recording is unbuilt: the current validation paths raise without appending a rejection event.

```
input
  → immune check (tiered cascade, §3 — gate / classify / reject-and-RECORD malformed; rejections are logged events)
  → AFFECT SPLIT: semantic payload → extraction;  affect metadata → parallel event field (never through extraction) [Inv. 11]
  → origin + claim + entity extraction (assign origin type, epistemic category, soft entity links)
  → Layer A append (event; source + timestamp; idempotency key)   [THE durable commit — Inv. 8]
  → entity_event_index updated SYNCHRONOUSLY, in the same transaction as the append (the one exception to "append is the only sync step" — it's a single cheap index write, and stale-detection races without it)
  → delta-reducer folds event into materialized Resolved View (async job; NOT in the append transaction)
  → enqueue audits/verification, under Budget Manager's idle schedule (§6) — off the hot path
  → (branch) process trace → §7, keyed by hypothesis_id for later oracle matching
```
A crash after append but before projection is recovered by re-folding from Layer A, not lost.

### Event taxonomy
`claim_asserted · observation_recorded · correction_appended · claim_questioned · claim_quarantined · claim_restored · gap_recorded · scope_mutated · verification_requested · verification_completed · entity_mention_recorded · entity_link_proposed · entity_link_accepted · entity_merge_accepted · entity_split_asserted · redaction_applied`
Process-trace records live in a **separate** store (§7) — model-performance facts are not claims about the world.

---

## 2. Epistemic metadata: origin, state, support

**Origin type is the primary field**, not confidence. Immutable per event (Invariant 5).

### Origin types
- **Observed** — direct system observation. Confidence = extraction/classification confidence.
- **User-stated** — the person asserted it. Two-claim split below.
- **Verified-external** — corroborated externally. Confidence = degree of *independent* corroboration.
- **Derived** — Layer B generation (inference/prediction/estimate/recommendation/summary). **Not stored by default.**
- **Personal / Unverifiable** — preference/private-context. User is the rightful authority. Confidence = confidence in *remembering*.

### The user-stated split
A user statement produces two claims: *"User asserted X"* and *"X is true."* Consistency may raise confidence in the **former**; not the latter, without independent support — **except** where the user is the rightful authority (preferences). "I prefer green glasses" → user is ground truth. "My laptop has 64GB" → user is a *source*.

### Two-dimensional state
```
verification_state: unverified | verified | questioned | quarantined | superseded
verifiability:      externally_checkable | locally_checkable | subjective | structurally_unverifiable
```
`Personal/Unverifiable` is `verifiability=subjective`, not a pseudo-failure state.

### State-transition contract
| From | To | Trigger | World oracle? | Offline allowed? |
|---|---|---|---|---|
| unverified | verified | independent corroboration | **Yes** | No |
| unverified | questioned | contradiction / structural issue | No | Yes |
| verified | questioned | contradiction / source drift / failed audit | No | Yes |
| questioned | verified | new independent corroboration | **Yes** | No |
| questioned | quarantined | failed audit / malicious source / invalid provenance | No | Yes |
| quarantined | questioned | privileged human restoration with reason | Yes / privileged | Maybe |
| — | — | Correction supersession: see [ADR 0004](../decisions/0004-correction-appended-supersedes-via-superseding-events.md); projector "1": [ADR 0018](../decisions/0018-correction-supersedes-candidates.md), subject to [ADR 0023 §5](../decisions/0023-stage-two-contract.md#5-corrections-are-deferred-under-version-1) | — | — |
| any | redacted | privacy/security/legal policy | privileged policy | Yes |

### Memory vs. derived (Invariant 7)
A derived statement is generated at answer-time and **discarded** — durable only via an oracle event that appends a **new** event. Confirmation *creates*; it never *promotes*. Observations do double duty: overriding a guess corrects the belief **and** grades the reasoning (§7).

### Support sets (Invariant 6)
The scalar example below is projector "0" only. For projector "1", see [ADR 0015](../decisions/0015-candidate-scoped-verification.md) and [ADR 0024](../decisions/0024-no-authoritative-head.md).

```json
{ "belief_id": "entity:legion/property:ram", "current_value": "64GB",
  "verification_state": "verified", "verifiability": "externally_checkable",
  "display_origin": "observed",
  "supporting_events": ["evt_scan_123","evt_user_456"],
  "opposing_events": ["evt_receipt_789"],
  "resolution_basis": "newer direct observation supersedes older purchase record" }
```

**Corroboration counts source classes, not events.** State thresholds treat each supporting event as a unit of evidence, but real ingestion is correlated by construction — multiple models sharing training data and the same prompt context, a Dream synthesis re-entering as a "new" event, one fact pasted from two documents. That's independent-looking corroboration that isn't independent, and it systematically overcalls VERIFIED in exactly a multi-model-council workflow. Fix: every event carries a `source_class` field; corroboration is counted in **distinct source classes**, not raw event count. Outputs from a shared context (e.g. a full council pass in one session) collapse to one class regardless of how many models produced them.

### Confidence governance (rules, not formulas)
**Two different things are both called "confidence" — separate them.** (1) **User-facing epistemic confidence** — a synthesized score shown to a person as "how sure is this claim." Deferred (V0 §3). (2) **Internal ordering scalar** — the legacy specification is in V0 §1; `ordering.claim_scalar` and `ordering.effective_confidence` remain stubs, and their broader consumers are unbuilt. For the implemented bootstrap-link treatment, see [ADR 0021](../decisions/0021-bootstrap-link-treatment.md).

Coefficients for any eventual synthesized (1) are TBD (§13), from runtime data. The system must satisfy: monotonic offline; corroboration gates state; minimum sample floor; decay is category-dependent and `as_of`-evaluated. For entity-link ceiling applicability, see [ADR 0021](../decisions/0021-bootstrap-link-treatment.md#3-confidence-ceiling-computation).

---

## 3. Governance components (closed list)

Each catches a distinct failure mode nothing else covers.

**Immune system — *prevent bad data entering, defense-in-depth*.** A **tiered cascade**, not a single gate. Adversarial-ML research has demonstrated single-layer prompt-injection detectors — including well-known open models — can be evaded at rates up to 100%; no single layer is trusted alone.
- **Stage 1 (deterministic, ~0 cost):** schema validation; regex for temporal/structural impossibilities.
- **Stage 2 (small, CPU-viable):** an existing purpose-built classifier (a Prompt-Guard-class model, ~20–90M params) for known attack patterns. Externally maintained — avoids owning a training/vetting pipeline for this stage alone.
- **Stage 3 (STLM, non-resident):** loads only for input still ambiguous after Stages 1–2. Intermittent cost, not continuous GPU residency. **Cold-start caveat:** the "adaptive, Dream-retrained" property is a *later* capability, not a v0 one. Dream ships in Phase 3 and the threat-signature corpus accumulates over time from zero — so until the corpus crosses a usable threshold, Stage 3 is a **static pretrained classifier**, functionally a second Stage 2, and should be described as such. Adaptivity requires Dream + a corpus + a retraining loop all existing; claiming "gets smarter over time" before those exist is the same overreach as claiming a confidence score that's deferred.
- **Stage 4 (LLM):** only payloads surviving all three reach Nyx Jr.
**Rejections at any stage must be logged events** — a silently-dropping gate is unauditable (its version of record-of-absence). Rejection recording is unbuilt; current validation raises without recording a rejection event. The Stage-4 survivor gets the **affect split** (Inv. 11). The STLM's **retraining pipeline is untrusted input**: signed/vetted signature sources, per-update audit trail, rollback-able, spleen halts retraining on false-positive spike, human sign-off until proven safe. *Immediate.*

**Liver — *re-evaluate existing memory*.** Periodic audit. Checks: evidence drift, source drift, staleness, dependency drift (§4). **Priority queue**, not full rescan — high priority: single-source, low-confidence-model-derived, old, heavily-referenced, suddenly-conflicting.

**Re-derivation cost is bounded by content-addressed dependency hashing (incremental view maintenance) — the same pattern incremental build systems use for cache invalidation, not a bespoke structure.** Each Layer B derivation stores a hash of the specific Layer A event IDs it depended on. On audit: hash unchanged → skip, zero-cost lookup; hash changed → only then trigger the expensive re-derivation LLM call. Converts Liver cost from scaling with *total-claims-×-time* to scaling with *actual-change-in-the-log*. Runs under the Budget Manager's `idle_compute_budget` (§6). *Periodic.* (Dependency hashing is implemented; queue-scoring defaults are specified in V0 §2. The Liver consumer and cascade budget remain unbuilt/open, §13.)

**Spleen — *observe system health*.** Observation only. Metrics: memory growth, confidence distribution, contradiction rate, quarantine rate, Dream yield, source-reliability trend, immune false-positive rate. Must have **thresholds + consumers**. Triggers: contradiction spike → re-prioritize liver; immune false-positive spike → halt retraining; anomaly → escalate to user. *Continuous.*

**Dream — *acquire + re-verify*.** Offline/background, under `idle_compute_budget` (§6). Discovered relationships route through the same oracle/write-exception rules as any derived hypothesis — never auto-stored. Carries the verification queue and drains **recorded gaps** as acquisition targets. *Background.*

**Verification oracle — *inject independent ground truth*.** Three classes (Invariant 4). Only a **world oracle** promotes world-belief.

**Offline reconciliation — *pay down verification debt*.** On reconnection, Dream drains the backlog in priority order before trusting anything gathered dark.

**User-in-the-loop protocol.** On ingest: user is told the origin/category, can correct it. On output: system discloses its own confidence and degraded state. Resolution path for queryable-origin contradictions (§5).

---

## 4. Failure modes and fixes

**Closed-loop / model collapse (silent, first).** → the **world-oracle** class specifically (Inv. 4) — re-derivation alone cannot break the loop.

**Recursive belief inflation.** → Inv. 5–7: derived statements never stored; only oracle-confirmed *events* enter Layer A.

**Resolved View drift / staleness & full-replay performance cliff.** → **decided**: materialized version-hashed delta-projection; stale-with-warning (implementation status in §1); replay scope follows [ADR 0012](../decisions/0012-whole-view-equality.md#explicit-whole-view-evaluation-exception).

**Layer A immutability vs. audit demotion.** → append-a-correction; ACC-lite (a **derivation validator**, Inv. 4) reads the Resolved View.

**Entity resolution time-travel.** A merge of A+B→C at T2 must not make a T1 event referencing A read as C. → **time-aware `as_of` projection**: events keep immutable pointers to the mention active at their time; merges alter the projection only forward from the merge event.

**Out-of-order fold at the reconnection seam (projector "0").** See §1's legacy observation value-recency rule. For projector "1", that behavior is superseded by [ADR 0024](../decisions/0024-no-authoritative-head.md).

**Non-deterministic replay via probabilistic entity links.** → entity-resolution **decisions** are explicit Layer A events; the resolver *proposes* (soft, out-of-log), Layer A *disposes*; the projection folds only over **accepted** decisions.

**Same-origin mutual destruction.** → **if the origin is queryable, query before demoting** (user-stated → inline clarification, §3); if fixed-in-time, mutual demote to QUESTIONED.

**Source-reliability sparse buckets.** → hierarchical prior with back-off; minimum sample floor.

**Immune training pipeline injection (sleeper).** The gate can be injected through its own training data and has no immune system of its own — reinforced by real evasion research showing single-layer detectors can be bypassed at up to 100%; the mitigation is the **tiered cascade** (§3), not one "better" detector. → treat signature updates as privileged untrusted writes.

**Dependency-drift cascades.** → transitive dependency tracking + cascade budget.

**Affective leakage.** → structural **affect split** (Inv. 11) as the primary mechanism; **metamorphic tests** as verification (semantically equivalent evidence differing only in tone must yield identical claim/route/state).

**Tuning emotion/expression parameters without leaking into the ledger.** Adjusting detection thresholds or expression mappings (Spleen weighting, `self_reference` ceiling, pivot triggers) must never become a runtime mode flag inside the live system — a scattered `if dev_mode` branch is exactly the kind of conditional that eventually leaves sandbox parameters shaping production, or lands sandbox events in the real hash chain. → **sandbox = a fork of the event log**, not a switch. Because the system already guarantees sweep/replay equivalence (§1, §4), a sandbox is canonical history copied into an isolated instance: mutate parameters there, replay, observe, discard — it never touches the real chain because it isn't the real chain. Two parameter classes behave differently and should be treated separately: **detection** parameters (what gets tagged as inferred affect at all) change the generated tag set, so forked output isn't directly comparable to canon without re-running both on the same input; **expression** parameters (already-tagged state → register/pivot/ceiling) are a pure function over existing events, so the same canonical events can be replayed through different expression configs and diffed directly. For live mid-session tuning, a parameter change is **its own logged event type**, auditable (you can see when Spleen weighting changed and to what) but explicitly outside the truth ledger — same non-promotion logic as `meta_commentary` — session-scoped by default, requiring a deliberate step to promote into canonical config.

**Oracle-linkage loss.** → process trace (§7) stored **before** the oracle event, keyed by `hypothesis_id` + semantic hash; background job matches oracle events to open hypotheses.

**Budget preemption / partial-state leakage.** → Preemption Protocol (§6): hard limit discards and quarantines; soft limit forces a clean wrap-up.

**Record-of-absence scope expiration.** → gaps carry a `search_scope_signature`; a `scope_mutated` event demotes affected gaps to QUESTIONED.

**Redaction/merge as belief laundering (promotion via destruction or pooling).** Recounting evidence after a redaction or entity merge can *raise* a belief's state as easily as lower it — destroying counter-evidence or pooling merged entities' events can cross a promotion threshold with no oracle involved. → Invariant 15: retroactive reinterpretation may demote or hold, never promote directly; would-be promotions emit a proposal into the normal gated path.

**Correlated corroboration (overcalibrated VERIFIED).** Multiple sources that share training data, prompt context, or origin (a multi-model council pass, a Dream synthesis re-entering as a new event, one fact pasted twice) count as independent corroboration when they aren't — silently overcalling VERIFIED hardest in exactly the workflow that produces the most events. → `source_class` field; corroboration counted in distinct classes (§2).

**Sweep/replay equivalence (twin of out-of-order-fold).** Incremental sweep on the materialized delta after a redaction or merge, versus full replay-from-genesis under the current redaction/merge set, are two independent derivation paths that can silently disagree — same class of bug as the value-recency guard (§1), invisible until traced against a belief that already crossed a threshold. → stated as a required equivalence, tested via the crash-point and sweep traces (§12); support graph is a DAG (stated invariant — a Layer-B-created cycle would loop the sweep).

**Two roots of state can't commit atomically (crash between key destruction and completion).** Chain (SQLite) and keystore are separate systems; a crash between destroying a key and appending `redaction_completed` lands in an uncovered state — a single-node design smuggling a distributed-systems problem. → the chain is already a write-ahead log of intent: startup scans for `*_requested` without a matching `*_completed` and rolls forward; keystore operations are idempotent so replay is safe. Requires crash-point traces (kill between every adjacent step pair, on paper) before trust, not just the happy-path trace.

---

## 5. Verification: oracle classes, online/offline, missing data, contradiction

**Three oracle classes** (Invariant 4): world oracle (promotes), derivation validator (validates synthesis, demotes/grades, cannot promote), structural auditor (demotes, cannot grade).

**Online (Dream's external re-check).** Expensive and rate-limited; this subsystem is unbuilt. For the independent-signal status of shipped direct observations, see [ADR 0001](../decisions/0001-observation-recorded-resolves-to-verified.md). (Caveat: the open web is often unfetchable — bot detection, 429s — so local corpus and oracle-confirmed events matter accordingly.)

**Offline.** Cannot confirm truth; triages. Three checks: internal contradiction (subject to queryable-origin rule below); re-derivation from Layer A (a *derivation validator*, highest yield, does not promote); provenance/plausibility (structural auditor). **Demote-only offline.**

**Contradiction resolution by origin queryability.** Queryable origin (user-stated, live source) → query before demoting; latest may supersede via retraction. Fixed-in-time origin → mutual demote, await an oracle.

**Missing data is first-class — a record of absence.** *Searched X, Y, Z on [date], tried [methods], found nothing.* Keeps "didn't look" / "looked, found nothing" / "doesn't exist" distinct. A gap carries a **`search_scope_signature`**; scope change → `scope_mutated` event demotes tied gaps to QUESTIONED. Becomes a Dream acquisition target; the honest substitute for provable completeness.

**Permanently unverifiable.** `verifiability = subjective | structurally_unverifiable`. Flagged, decays, never promoted.

### Erasure execution (two-phase, provenanced)
`redaction_requested` (event ids, reason class: credential/PII/legal/user-request, authorizer) → key destroyed → derived sweep (walk every support set citing the redacted event's payload; Resolved View rows, syntheses, Dream outputs invalidated or regenerated — the entity_event_index sync makes the sweep set computable without a full replay) → `redaction_completed` (records what was invalidated). The erasure itself carries full provenance. **Replay after redaction:** `replay(t)` for a redacted event yields a typed `REDACTED` sentinel — envelope survives (type, occurred_at known), payload doesn't — even when `t` predates the redaction; replay is deterministic as a function of `(chain, current redaction set)`, not of what an observer at `t` originally saw. That's the honest, stated cost, not a discovered inconsistency.
**Evidentiary contribution on redaction:** collapses from `content(N)` to `envelope(N)`. A belief depending only on "an event of this type occurred at T from actor A" survives on envelope facts. Anything depending on *what N said* loses that support edge — the edge is no longer re-derivable, and an unfalsifiable support edge under a VERIFIED belief violates the system's own epistemology. In practice, since almost all support is content-based, a redacted event drops out of corroboration counting.

---

## 6. Proportional routing + Budget Manager

### Cost tiers: governance is exception machinery, not default machinery
Reading the invariants as "every write touches the full apparatus" makes the system look heavier than it runs. It doesn't, once stated explicitly:
- **Routine read:** hits the materialized Resolved View (§1), returns. No oracle, no liver, no support-set expansion — those exist for when the Belief Inspector (§8) is opened, not for every answer.
- **Routine write (target):** immune Stages 1–2 (cheap, deterministic/CPU) → append → async delta-reduce. Liver, verification enqueue, and process-trace run **off-path**, under the Budget Manager's idle schedule (below) — never blocking the write. These broader consumers and the asynchronous worker are unbuilt; shipped wrapper publication is synchronous after the separate append commit (§1).
- **Escalation triggers:** a contradiction is detected; stakes are flagged (governance depth); a cheap check fails and Stage 3/4 of the immune cascade is needed; the user opens the Inspector; an oracle event needs hypothesis matching.

This is the concrete answer to "keep every feature without the system feeling heavy": nothing is cut — most of it just doesn't fire on the common path.

### Triage-then-escalate
The same pattern resolves three problems: **model selection** (Nyx Jr classifies intent/domain, checks a **capability registry**, routes on `model score × relevance`, escalates when no local model clears threshold), **governance depth** (above), **verification spend** (offline triage decides what merits an online check).

**Capability registry** (required): per-model task types, quantization, load/availability, reliability scores by domain (updated from §7 traces). Escalation-tier candidates (OpenRouter, below-frontier cost): **GLM** and **Qwen** coder variants for routine code-check/audit; reserve frontier for high-stakes work. Versions/pricing shift fast — verify before spend. (Separately: speculative decoding — a small draft model proposing tokens a large model verifies in parallel, e.g. DSpark-style — is a safe local-inference speed optimization for the *reasoning tier itself*, orthogonal to epistemic governance; TBD to evaluate, §13.)

### Budget Manager — policy layer, not the enforcement mechanism
Enforces finite CPU/VRAM/token/time/verification budgets by **deciding what runs and in what priority** — it does not reinvent preemption. Two enforcement paths, because they're mechanically different problems:
- **CPU-bound work** (SQLite I/O, hashing, queue management): enforced via OS/driver primitives (`nice`/`ionice`, cgroups) — mature, not custom-built.
- **GPU-bound work** (STLM/LLM inference): a dispatched kernel **cannot be mid-execution interrupted** — a hardware/driver limit, not a design choice. The real mechanism is the Budget Manager **stops submitting new background GPU work** the instant foreground work exists, rather than "instantly revoking" work in flight. Precise framing so the design doesn't assume a guarantee hardware can't give.

**`idle_compute_budget`:** Dream and Liver run only under this cap, released only when no foreground query is pending — this is what keeps background governance from competing with the user for the same hardware (the unbounded-Liver risk in §4).

**Mechanizes demote-only-offline** (§5): disconnected → online-verification budget = 0, hence debt accumulates rather than resolving. Token-budget readout = the **context meter** (§8).

**Preemption Protocol.** Hard limit → abort, discard partial output, write **nothing** to Layer B, route to quarantine. Soft limit → inject a "wrap up" directive.

---

## 7. Meta-learning: the process trace

**The belief store never learns from inference; the model-trust layer does.** An inference outcome is a fact about the **model**, not the world — updates source reliability, routing, calibration.

**Store the process, not the answer.** Model, evidence available, retrieved vs. missed, failure class, correction. Lives in a **separate store from Layer A**: **crash-durable (WAL + fsync) but mutable — explicitly NOT append-only.** Grading updates a trace in place after creation (ungraded → graded), so it cannot carry Layer A's immutability guarantee; the earlier "same guarantees as Layer A" phrasing was wrong, since immutability *is* Layer A's defining guarantee and this table deliberately lacks it. The requirement is durability, not immutability — "outside Layer A" must not mean "loses data on log rotation," but it also must not be read as "append-only like Layer A."

**Oracle matching.** Each trace is written **before** any confirming oracle event, keyed by `hypothesis_id` + semantic hash. A background job matches oracle events against open hypotheses: matched → graded; unmatched → just a new fact. *(This hash and the Liver's dependency hash, §3, are the same underlying pattern — content-addressed "has the thing this depended on changed." They should share one canonical hashing utility, §13, not two ad hoc ID schemes.)*

**Three failure classes → three fixes:** missing information (Dream acquisition + calibration); overlooked information (retrieval-quality fix); wrong model (routing/registry update).

**Oracle-gated.** Only an independent verdict lets you learn from an outcome. Absent one, discard, no lesson.

Third occurrence of one primitive: **outcomes update trust in a *producer*, never belief about the *world***.

---

## 8. State disclosure / UI — a trust instrument

Optimizes for **trust, not chat**. UI-constitutional rules:

- **Origin first, not score.** Never render decimal confidence (Inv. 2).
- **Unverifiable-by-design is a first-class visual state**, not a QUESTIONED look.
- **Separate truth-state / operational-state / memory-state** visually.
- **Stale-projection warning** when a read is served against a not-yet-caught-up view (§1). This disclosure ships for projector "1" belief reads; version "0" reads remain unlabeled. The current freshness contract is in [ADR 0014 §8](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#8-append-freshness-and-derived-progress).
- **Degraded states surface their own explanations; healthy states stay silent.**
- **Personality narrates state but never blurs magnitude** (Inv. 11).
- **Progressive-disclosure tiers, no upward leak.** One always-visible signal; per-claim state at reading tier; Belief Inspector / metrics at inspect tier.
- **Context meter** — token budget (§6), color-banded by headroom.

**Belief Inspector:** why do you believe this (support set), what would change your mind (demotion triggers), how did this change over time (`as_of` replay).

**Ingest-classification affordance,** governed by Invariant 13: hints, not gates.

**Out-of-scope explainer** is first-run/help copy, not runtime UI.

---

## 9. Executive loop (agent layer — v2, on top of the kernel)

```
current epistemic state (Resolved View)
  → work
  → candidate observations
  → GOVERNANCE FILTER (subtractive — most candidates discarded; storage is the exception)
        ├→ memory updates → Layer A (only what cleared governance)
        └→ process trace → §7 (keyed for oracle matching)
  → continue?
        ├ done
        ├ loop again
        ├ ESCALATE TO HUMAN (blocked on verification / unresolved contradiction)
        └ budget-stop (Budget Manager + Preemption Protocol, §6)
```
Storage is the exception; every pass grades its own reasoning; the loop knows when to stop and ask.

---

## 10. Design filter & scope boundaries

- **Governance** → *inside* the kernel. §3 list is closed.
- **Application** (Skopos, carbon-credit verifier, trading scorer, the agent loop) → *on top*.
- **Everything else** → out.

**World Model — out of scope for v1 (deliberate).** Nyx governs belief, not action.

**Platform vs. apps.** **Nyx** = platform. **Skopos** = flagship application (the showcase, not a competing project). **eTPS** = separate methodology, outside the stack.

**Agent-to-agent / site-side endpoints (forward note).** Provenance makes a site's *claims* verifiable but proves *presence*, not *completeness* — the visitor must source-score the endpoint. Honest gap-reporting (§5) makes such endpoints measurably faster to agents.

---

## 11. Identity Layer — v1 minimum now, full graph v2

**Identity implementation status:** scoped bootstrap ships under projector "1". Scored matching links and the full identity graph remain unimplemented. Current stage scope is governed by [ADR 0023](../decisions/0023-stage-two-contract.md).

**Danger addressed is false *sameness*.** Identity is **soft and reversible**.

**Identity-link state and confidence:** the former uniform scored-link minimum is superseded for bootstrap by [ADR 0021](../decisions/0021-bootstrap-link-treatment.md). **Invariant:** no claim enters active resolved belief without an explicit entity-link state. See that ADR for the applicable state and ceiling treatment.

**Determinism preserved** (Inv. 9): resolver **proposes** (soft, out-of-log); Layer A **disposes** (accepted decisions are explicit events); the projection folds only over accepted decisions. Time-aware: merges alter the projection only forward from the merge event.

**Merges are a promotion vector — gated accordingly (Invariant 15).** Merging two entities pools their events; if the pooled corroboration crosses a state threshold that neither entity's history cleared alone, that's evidence reinterpretation auto-promoting a belief, the mirror image of redaction destroying counter-evidence to the same effect. A merge may hold or demote a pooled belief on recount; a would-be promotion routes through the normal gated path and must re-earn its state from surviving positive evidence — the merge event itself does not promote it.

**Erasure keys bind to `canonical_entity_id`, not `mention_id`.** Per-subject crypto-shredding keys (§5) are meaningless pinned to a pre-resolution mention — a key tied to a mention that later merges into a different canonical entity has no clear owner. Keys resolve post-merge/split against the current canonical identity.

**v2 full graph:** lifecycle `mention → candidate → canonical → merged → split`; two confidence tracks (claim vs. entity-link, latter a ceiling); merges are events not mutations; resolver never auto-collapses on similarity; offline merges propose-only; contradiction vetoes merges.

Target: **"Nyx knows which thing a fact belongs to, how sure it is about that link, and how to unwind it when the guess was wrong."**

---

## 12. Implementation sequencing

The spec above is deliberately more complete than month-one code — that is what a spec is for. What ships first is narrower, and nothing here is cut *from the architecture*, only deferred *from the first build*:

- **Phase 1:** Layer A (SQLite events table, trigger-enforced append-only), Immune Stages 1–2, basic materialized Resolved View (delta-reducer, version hash), Constitution invariants 1–9. Enough to durably store and read governed beliefs.
- **Phase 2:** Liver with a real priority queue and the dependency-hash mechanism (§3); Budget Manager's idle-gating and policy/enforcement split (§6).
- **Phase 3:** process-trace + oracle matching (§7), Identity Layer v1 soft-linking (§11), verification debt + offline reconciliation (§5), immune Stage 3 (STLM tier — ships **static**; adaptivity waits on a threshold-sized threat corpus, §3). The `occurred_at` value-resolution prerequisite applies to projector "0"; for projector "1", see [ADR 0024](../decisions/0024-no-authoritative-head.md).

The full spec stays the reference; this is the order reality gets checked against it.

### Pre-coding trace gate (extends V0 §5)
Before erasure or identity-merge code is trusted: (1) redact one of three supporting events under a VERIFIED threshold, confirm the belief lands at the correct demoted state via both incremental sweep and full replay, confirm they agree; (2) merge two entities whose pooled events would cross a VERIFIED threshold neither cleared alone, confirm hold-plus-gated-proposal, not auto-promotion; (3) kill the process between each adjacent step of the redaction sequence (`requested` → key destroyed → sweep → `completed`), confirm startup roll-forward converges and sweep/replay equivalence still holds after recovery.

### Executable invariants, not just reviewed ones
Determinism makes these traces near-free to run as permanent property tests (e.g. property-based testing generating event sequences plus redactions plus merges): assert incremental fold ≡ replay-from-genesis under the current redaction/merge set; assert the support graph stays a DAG; assert no state transition ever promotes as a side effect of redaction or merge. The worked traces above become golden fixtures, run on every change — this is the fix for the review-vs-execution blind spot named in the council doc: the council can review an artifact; only a harness can run it.

---

## 13. Open implementation TBDs

- Liver scoring defaults are specified in V0 §2 and stored in `src/nyx/config.py`; the queue, cascade **budget + transitive depth**, and empirical retuning remain open.
- Event serialization, ordering, idempotency, and hash chaining ship in `src/nyx/hashing.py`, `events.py`, `projection.py`, and `storage.py`. Checkpoints and a standalone replay-verifier subsystem remain unbuilt.
- Reducer/evaluation contracts are governed by [ADRs 0010](../decisions/0010-projection-parameters.md), [0012](../decisions/0012-whole-view-equality.md), and [0014](../decisions/0014-cross-belief-reducer-and-hash-lineage.md); stage-two implementation ships. Database compatibility policy is governed by [ADR 0011](../decisions/0011-database-schema-versioning.md), with current version selection in [ADR 0017](../decisions/0017-schema-version-3.md). Decay evaluation remains deferred. The legacy `occurred_at`/rowid value tie-break is projector "0" only; see [ADR 0024](../decisions/0024-no-authoritative-head.md) for projector "1".
- **Unified hashing utility** is implemented in `src/nyx/hashing.py`; Liver and process-trace consumers remain unbuilt.
- `idle_compute_budget` defaults are specified in V0 §2 and stored in `src/nyx/config.py`; enforcement and empirical retuning remain unbuilt.
- Spleen threshold defaults are specified in V0 §2 and stored in `src/nyx/config.py`; monitoring is unbuilt. Confidence math coefficients remain deferred pending runtime data.
- Immune signature-update vetting: automated source-trust vs. human sign-off.
- Hierarchical-prior back-off cutoffs.
- Reconnection reconciliation ordering.
- Entity resolver similarity thresholds; entity-link ceiling composition on multi-hop; merge-suspicion signals.
- Process-trace schema exists in `schema.sql`; handlers and retention remain unbuilt.
- Record-of-absence schema exists in `schema.sql`; handlers and `search_scope_signature` computation remain unbuilt.
- Erasure mechanism choice per data class (crypto-erasure vs. redaction-event).
- Preemption Protocol quarantine-bin handling.
- **Speculative decoding** (draft-model + large-model verification, DSpark-style) as a local reasoning-tier speed optimization — orthogonal to governance, evaluate independently.
- DuckDB for Spleen's analytical queries — **deferred/optional**, only if aggregate queries become a bottleneck at real scale; not needed now.
- **Personality-emergence layer (unspecified — do not assume it exists).** Invariant 11 now references a "personality-emergence monitor" that owns the `self_reference` drift metric, but the layer itself — how register/entrenchment/gravity are computed, what Spleen contributes to stylistic register, the emergence-detection model — has **not** been specified or council-reviewed. Only the `meta_commentary` tagging + ceiling mechanism is decided. The monitor is currently a named read-side sweep over `meta_commentary`-tagged events, nothing more. Open boundary question deferred to §8-emergence when written: may `self_reference` reference inferred emotional state at all ("I'd find that ironic, if I found things"), or strictly external callbacks? Former is richer and a harder firewall to hold; latter is trivially safe. This is a values call, not a mechanism one, and is **not** yet made.

---

## 14. Glossary

- **Epistemic kernel** — protected core governing what is believed and how beliefs are earned.
- **Reality Layer (Layer A)** — append-only `events` table, engine-enforced. The epistemic ground record.
- **Resolved View** — materialized, version-hashed, deterministic projection via a delta-reducer, `as_of` an explicit time. Replay scope follows [ADR 0012](../decisions/0012-whole-view-equality.md#explicit-whole-view-evaluation-exception).
- **Cost tier / hot path** — the explicit split between the cheap default path (routine read/write) and the escalation path (full governance). Governance is exception machinery, not default machinery (§6).
- **Origin type** — primary metadata determining what a claim's confidence means. Immutable per event.
- **Support set** — the set of supporting/opposing/superseding/gap events a resolved belief folds.
- **Oracle (three classes)** — world oracle (promotes), derivation validator (validates/demotes/grades, cannot promote), structural auditor (demotes only).
- **Content-addressed dependency hash** — the mechanism bounding Liver re-derivation and process-trace oracle matching: hash what a derivation depended on, compare, redo work only if changed. Same pattern as incremental build systems (Nix/Bazel).
- **Derived statement** — a Layer B generation. Transient; enters Layer A only via a new oracle-confirmed event.
- **Entity / entity-link confidence** — a thing a claim is about; bootstrap-link state and ceiling applicability are governed by [ADR 0021](../decisions/0021-bootstrap-link-treatment.md).
- **Process trace** — record of how a reasoning attempt went. Separate store, same durability as Layer A.
- **Record of absence / gap** — an event documenting a search that found nothing, carrying a `search_scope_signature`.
- **Verification debt** — backlog of QUESTIONED items an offline node couldn't resolve.
- **Quarantine** — isolation of a failed-audit record, retained for inspection.

- **Envelope / payload** — the split that makes erasure compatible with append-only: the hash chain covers the envelope (id, type, occurred_at, hash) only; the payload is separately destroyable via key destruction without breaking chain verification.
- **Source class** — the field distinguishing genuinely independent corroboration from correlated ingestion (shared model context, re-entrant synthesis, duplicate pasted origin). Corroboration counts distinct classes, not raw events.

---

## Carryover from prior records (context; reconciled with current invariants)

Three-tier cognitive stack (small → Dream → large). ACC-lite is a **derivation validator** (Inv. 4), not a world oracle; coverage bounded by what's stored. Rules 14/15 (model confidence = annotation, not gate). SQLite schema: WAL mode, `events` table with UPDATE/DELETE-blocking trigger, schema versioning. The earlier `peak_score`, `last_known_score`, and `dream_source_map` references are historical and absent from shipped `schema.sql`. **Correction:** "soft deletes" contradicts Invariant 1 — replace `deleted_at` flags with an appended `superseded_by`/`retracted` event. Repo: axendo79/nyx-memory. P0 fixes (re-sequenced): projection model **decided** (materialized-delta) → `safe_append_event` (formerly safe_write_jsonl) → monotonic-growth test extended to process-trace + record-of-absence substrates → second-order injection in THREAT_MODEL.md (now addressed structurally by the tiered immune cascade, §3) → fsync/orphan-.tmp handling → ~~Python 3.14→3.11/3.12~~ (SUPERSEDED by decisions/0009: 3.14 re-adopted as the target; the downgrade was never enforced and the suite is green on 3.14).
