# Blocked-gap decision worksheets

**decision packet — not a decision.** Non-authoritative, prepared 2026-10-15
against `31f93bb93b6748e4e3f619c0fb0f70d7599f6929`. All options below are
**unselected**. Recommendations are advice to Josh, not rulings, defaults,
ratification, implementation instructions or gap closures. No code, test,
authority record or existing gap status changes here.

This follows PR #22's [payload](2026-10-14-duplicate-key-payloads-worksheet.md)
and [O3](2026-10-14-o3-listing-search-worksheet.md) worksheet pattern: observed
boundary, exact question, alternatives, consequences, recommendation and future
implementation/evidence. Line citations identify the unchanged
[GAPS.md](../GAPS.md) at the baseline above; the
[pinned register](https://github.com/axendo79/ProjectNyx/blob/31f93bb93b6748e4e3f619c0fb0f70d7599f6929/GAPS.md)
preserves those line numbers after later edits.

“Unlocks” always means **after the necessary accepted decision and confirmed
maintainer authority commit**, with its complete schema/algorithm/failure/test
contract. Selecting a direction alone does not fill its missing mechanics.
Evidence-only options unlock specification work, not production handlers. Frozen
projector bytes/refusals, append-only Layer A, deterministic genesis replay,
candidate-scoped support, no silent promotion and accepted public-corpus policy
constrain every option. A contrary choice requires an explicit authority amendment.
No numeric threshold, new projector allocation or missing payload shape is supplied.

## Coverage index

| Register entry and baseline lines | Worksheets |
|---|---|
| Cross-belief seam resolved; merge/split stage pending, 19–42 | W01 |
| Redaction breaks write/replay, 59–68; corpus restriction R4, 339–348 | W02 |
| External source-report O2 deferred remainder, 163–179 | W03, W17, W18 |
| Listing/search O3, 181–196 | W05; companion ratification packet |
| Whole-store growth O4, 198–216 and measured follow-ups 218–337 | W06, W07 |
| Rename identity deferred remainder, 350–363 | W04, W19 |
| Queue 6 mutation scope, 400–460 | W08–W11, one worksheet per finding |
| Queue 6 legacy rebuild boundary, 462–481 | W12 |
| Duplicate-key payloads, 492–589 | W13; companion ratification packet |
| Cross-language canonicalization/independence, 591–658 | W14 |
| Timestamp representation follow-up, 680–698 | W15; boundary refusal is resolved |
| Backdated corrections, 704–719 | W16, W07 |
| Origins beyond observed, 721–736 | W17 |
| Candidate correction residual, 738–786 | W18; ordinary projector-3 operations are implemented |
| Existing-subject association/multi-user authority, 802–808 | W19 |
| Mention correction, 810–813 | W20 |
| Existing-candidate support attachment, 815–819 | W21 |
| Retention/coalescing/temporal resolution, 821–834 | W06, W07 |
| Usage recording, 836–843 | W22 |
| Dream emission operations, 845–888 | W23.1–W23.8, all eight listed decisions |
| Additional scalar reads, 890–895 | W24 |
| Later links/support-dependent transitions, 897–902 | W25, W26 |
| Noted idempotency event-type distinction, 915–920 | W27, a contingent change rather than a correctness fix |

There are **34 worksheets**: W01–W22, the eight W23 subworksheets, and W24–W27.
Resolved entries are not reopened. In particular, shared-time whole-view equality
(117–131), schema-5 constraints (788–800), Stage 1 domain refusal and writer/default
fixes do not need new decisions. `gap_events` (927–929) is explicitly an absent
handler rather than a recorded decision; no speculative worksheet is invented.
The resolved writer entry's deferred transport/import/recovery procedures
(149–161) remain outside shipped scope; nothing here authorizes them.

## W01. Merge/split and the stage-three release boundary

**Source:** GAPS.md lines 19–42. Accepted ADRs
[0013](../decisions/0013-cross-belief-identity-semantics.md),
[0014](../decisions/0014-cross-belief-reducer-and-hash-lineage.md),
[0015](../decisions/0015-candidate-scoped-verification.md) and
[0023](../decisions/0023-stage-two-contract.md) govern identity, lineage, standing
and current stage refusals. Proposed [0027](../decisions/0027-stage-three-authority-and-acceptance.md)
is Gate-1 incomplete. Its old projector/schema allocations require reconciliation
with later ADR 0034 and any later accepted bundle; numbers alone confer no support.

**Question:** what preparation/release scope should precede any merge, split or
corroboration handler?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Continue the shipped stage boundary | All current refusals persist; feature delivery waits. | No new stage-three handler. |
| B. Complete a protected-stage-three candidate, separately from destruction | Finish B1–B5 schemas, private codec, compound custody, service records and vectors; obtain independent Gate 2 review before ratification. First-write protection/custody cannot be postponed. | After ratification, the bounded protected identity/corroboration implementation; genuine private use still requires Gate 3 and R4's erasure conditions. |
| C. Prepare one combined protected/erasure release | Larger specification/review scope and explicitly reallocated versions; test identity and destruction together. | Only after both completed contracts are accepted: combined handlers and deployment proof. |

**Recommendation:** B for specification preparation, keeping A's runtime boundary.
Do not treat either requested 0036/0037 source audit as Gate 2 review of 0027.
**Evidence required:** compound split/remerge fixtures, independent vectors,
complete affected-set replay, crash/restore proof and recorded review exclusions.

## W02. Redaction, erasure and the public-only corpus boundary

**Source:** GAPS.md lines 59–68 and 339–348. Accepted
[0002](../decisions/0002-payload-stored-plaintext-in-v0.md) keeps plaintext;
[0031 section 7](../decisions/0031-source-report-claims.md#7-corpus-policy-and-derived-copy-inventory)
keeps public-only policy until the specified erasure requirements are accepted,
implemented and passed. Proposed [0028](../decisions/0028-redaction-and-crypto-shredding.md)
has unresolved manifests, capsules, pruning, overlays and evidence profiles;
missing payloads and a REDACTED string are not its implementation.

**Question:** which erasure/deployment scope should be developed before any
protected corpus is admitted?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain public-only operation and explicit redacted-history refusal | No privacy/deletion guarantee; existing corpus policy remains enforceable. | No erasure handler or private intake. |
| B. Complete a fresh protected-format/erasure contract first | Close inherited 0027 blockers, exact erasure records, copy closure, custody/witness and restore semantics; independently qualify implementation/provider/host. | After acceptance: sealed first-write paths, typed unavailable reads, erasure execution and replay overlays; private deployment only after all R4 conditions pass. |
| C. Add explicit legacy enrollment/sanitization to B | Must inventory old plaintext, immutable copies and original signatures; some datasets may be ineligible. | Additional conversion/refusal and cleanup tooling only for demonstrably eligible units. |

**Recommendation:** B's specification/evidence track while A remains in force;
handle C as separately authorized, dataset-specific work. No acceptance shortcut
comes from deleting rows or inventing a sentinel. **Evidence required:** frozen
closures, unavailable-content verification distinctions, interrupted destruction,
restore non-resurrection and all managed copies, including outputs and backups.

## W03. Deferred external-report producers

**Source:** GAPS.md lines 163–179 and 350–363. Accepted
[0031](../decisions/0031-source-report-claims.md) ships literal ADR slice 1,
not Git-report slice 1b or web/PDF capture. The earlier
[capture worksheet](2026-10-05-slice2-capture-worksheet.md) details C1–C10;
model-written summaries also need W17's separate origin contract.

**Question:** which next report producer should receive a bounded contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep literal ADR reports only | Closed vocabulary, exact pinned artifacts and specialized version guards persist. | No new producer. |
| B. Specify Git-report slice 1b first | Decide exact Git transcript, vocabulary, acquisition/request retention and scope; rename evidence remains report-scoped. | Reviewed Git capture/import and offline provenance checks. |
| C. Specify pinned public web/PDF captures first | Decide bytes/redirects/time/resource bounds, extractor/location mapping, identities, admission and backup closure. More acquisition dependencies. | A finite capture/extraction/import slice; no summary-as-world-truth or automatic report correction. |

**Recommendation:** B as the smaller next extension; C remains an independent
product priority choice. Neither reuses slice 1's allowlist by implication.
**Evidence required:** exact source/quote reproduction offline, saved-request
retry after actual failure, admission bypass tests and preserved old reader guards.

## W04. Rename reporting versus identity association

**Source:** GAPS.md lines 350–363. ADRs
[0019](../decisions/0019-identity-bootstrap.md),
[0020](../decisions/0020-multi-user-authority-undecided.md) and
[0031 section 6](../decisions/0031-source-report-claims.md#6-rename-identity-and-adr-numbers)
preserve repository/path scopes. The frozen `902467a` R092 fixture does not
establish common subject identity.

**Question:** what should later rename ingestion assert?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Preserve the present literal-only surface | Renamed paths stay separate subjects with no new rename producer. | No new handler. |
| B. Add report-only rename/similarity observations | Capture what pinned Git output said; keep old/new scoped subjects and candidates distinct. | Slice-1b report vocabulary, capture and named provenance, after W03's contract. |
| C. Also seek explicit identity association | Rename detection alone is insufficient; decide admissible basis and historical authorization under W19/W01. | Separately ratified association/merge handling, never similarity-driven auto-merge. |

**Recommendation:** B, without C. **Evidence required:** R092 versus later Python
ADR number reuse, exact path/revision scope, all candidates retained and no
association inferred from text, number, digest or similarity.

## W05. O3 public discovery

**Source:** GAPS.md lines 181–196. Proposed
[0037](../decisions/0037-o3-mention-discovery.md) and shared Proposed
[0036 V1–V9](../decisions/0036-strict-payload-keys.md#shared-version-boundary)
record Josh's **B** and follow-up answers for drafting only.

**Question:** ratify the prepared index contract or revise the representation?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Rework as an explicit scan API | Avoid index tables but retain the complete query/version/freshness contract and proportional scan cost. | A separately ratified scan surface; requires revising the current B draft. |
| B. Ratify the prepared same-database index and joint bundle | Exact literal search, typed complete traversal, stale disclosure, restart cursors, explicit enrollment and atomic publication. | 0037's 12 acceptance families after both authority receipts and dependencies. |
| C. Rework as a separately anchored sidecar | Adds independent store/prefix binding, publication, backup and recovery failure states. | A newly specified sidecar/query contract, not today's proposal. |

**Recommendation:** B, consistent with the recorded ruling; the remaining action
is formal ratification, not another inferred design answer. See the
[ratification packet](2026-10-15-ratification-packet-adr-0036-0037.md).
**Evidence required:** independent all-row completeness, missing/extra rows,
mention-only membership, joint crash recovery and read-only query witnesses.

## W06. Whole-store growth and historical tree retention

**Source:** GAPS.md lines 198–216, 240–337 and 828–834. Accepted
[0025 sections 5–7](../decisions/0025-incremental-result-commitment.md#5-incremental-representation-and-atomic-publication)
retain immutable nodes. The 2,400-event fixture used 86,559 nodes and 48,660,480
file bytes; these are fixed-workload observations, not a universal growth bound.
Later verifier optimizations changed work, not retention policy.

**Question:** what storage lifecycle should a later design support?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain all nodes and measure | Maximum present historical availability; growth continues. No threshold is inferred. | Measurement/reporting within existing semantics; no reclamation. |
| B. Reclaim only derived nodes outside an explicitly retained root set | Must define root/prefix/proof availability, replay reconstruction, writer/read isolation and crash-safe reclamation; Layer A stays complete. | Versioned reachability/GC and on-demand explicit reconstruction under a ratified historical-access contract. |
| C. Archive historical derived stores with a complete log and inventory | More restore/availability operations; decide exact artifact/anchor and managed-copy retention. | Explicit archive/export/restore tooling and cold-history reads under a new contract. |

**Recommendation:** A now; develop B's root-availability specification before
reclamation. W07's candidate semantics are a separate decision. **Evidence required:**
same fixed corpus before/after, complete old-prefix replay/own lineage, retained
proof behavior, byte inventory and actual GC interruption/recovery. Set thresholds
only by a later explicit capacity decision.

## W07. Candidate retention, coalescing and temporal applicability

**Source:** GAPS.md lines 821–834 and 704–719. Accepted
[0023](../decisions/0023-stage-two-contract.md),
[0024](../decisions/0024-no-authoritative-head.md) and
[0034](../decisions/0034-forward-state-transitions.md) retain candidates and distinguish
log-ordered live status from world-validity. The
[valid-time worksheet](2026-10-05-valid-time-worksheet.md) remains advisory.

**Question:** should a future contract add temporal resolution or semantic compaction?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain all candidates; use accepted explicit forward operations | Existing live/retained history stays complete; no world-validity answer or automatic aging. | No new temporal/coalescing handler. |
| B. Add explicit recorded applicability/interval assertions | Decide authority, unknown validity, interval boundaries, overlaps, knowledge cutoff and ambiguity. Keep all source candidates. | Separately selected bitemporal/set-valued applied-state reads and recorded applicability events. |
| C. Seek semantic coalescing or candidate retirement | Must define exact claim/evidence identity, old-cutoff recoverability and retained provenance; value equality is insufficient. | Only a separately ratified compaction model and compatibility path. |

**Recommendation:** A for present use; B if external-time answers are the intended
deliverable, before C. Physical node GC is W06. **Evidence required:** late knowledge
about earlier intervals, overlaps returning ambiguity, equal values with different
standing, all old IDs/provenance retained and no recency-selected scalar.

## W08. Mutation escape: reserved payload key-binding metadata

**Source:** GAPS.md lines 420–425 and 453–460. Altering
`payloads.canonical_entity_id` escapes all four projectors' verifier checks. It is
outside the current envelope/content commitments; no key binding is implemented.

**Question:** what assurance should this reserved field carry?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Explicitly classify it as unauthenticated reserved metadata | Preserve historical stores and state the limit. | Disclosure only; no claim that a verifier pass authenticates it. |
| B. Define a profile-specific NULL-only/inert-field rule | Detect non-NULL changes only where that rule is recorded as applicable; legacy non-NULL treatment needs a compatibility decision. | A scoped verifier/admission rule and negative fixtures. |
| C. Define an authoritative recorded binding/independent commitment | Must decide custody unit, identity transitions, commitment version and historical interpretation; ties into Proposed 0027/0028. | Versioned binding construction, validation and tamper detection after the complete protected contract. |

**Recommendation:** A now; C only with the full custody protocol. A NULL-only rule
must not masquerade as cryptographic key ownership. **Evidence required:** all four
mutation cases, NULL/non-NULL history compatibility and independent binding checks
if C is chosen. No present Layer A rewrite follows from any recommendation.

## W09. Mutation escape: lost versus originally absent legacy progress

**Source:** GAPS.md lines 426–430. A missing/relabelled legacy `derived_progress`
row yields explicit unknown freshness. Existing checkpoint-less legacy stores
are supported; the log cannot distinguish original absence from later loss.

**Question:** should a recorded expectation make legacy checkpoint loss an error?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Preserve unknown freshness without a failure exit | Honest existing compatibility, but no detection of lost versus never-created rows. | No new checkpoint guarantee. |
| B. Introduce an explicit trusted enrollment/baseline declaring required progress | Must specify durable basis, store identity, exact covered versions/prefix and restore semantics. | Verifier distinguishes optional historical absence from missing mandatory state. |
| C. Require progress for every legacy store in a new compatibility contract | Old unmarked stores refuse until an explicit validated transition; cannot infer a checkpoint from hashes/time. | Strict legacy open/verify and baseline tooling after an accepted migration contract. |

**Recommendation:** A until B's independent basis is defined; prefer B over
retroactively imposing C. **Evidence required:** originally absent and deleted
fixtures, relabelled version, copied/restored store binding and refusal without
guessed progress. Rebuilding state alone cannot prove a historical checkpoint existed.

## W10. Mutation escape: stored evaluation-time claims

**Source:** GAPS.md lines 431–436. The standalone verifier excludes
`resolved_beliefs.projected_as_of`. Accepted
[0012](../decisions/0012-whole-view-equality.md) compares every field at a specified T;
[0014 section 7](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#7-lineage-is-separate-from-whole-view-equality)
excludes evaluation-only fields from lineage.

**Question:** which explicit basis should an audit use to verify stored evaluation time?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep the current unchecked disclosure | A passing lineage audit makes no stored-evaluation-time claim. | No new timestamp audit. |
| B. Add a separately requested shared-T evaluation audit | Caller names T/cutoff/version; distinguish reconstructed-at-T equality from authenticating historical per-row evaluation. Mixed live-row times remain expected. | Explicit whole-view audit/results with a precise comparison basis. |
| C. Record independently trusted publication/evaluation receipts | Requires durable authority, per-row or publication association, retention and restore rules; not inferred from current values. | Authentication of a historical stored evaluation claim plus receipt verification. |

**Recommendation:** B for callers needing shared-time comparison; retain A's
limit for ordinary verification. C only if historical evaluation provenance is
actually required. **Evidence required:** changed/swapped times, differing live
publication times and a time-dependent projector; no guessed T or hash-only equality.

## W11. Mutation escape: operational `updated_at`

**Source:** GAPS.md lines 437–440. `entity_event_index.updated_at` is an
uncommitted operational clock diagnostic; Layer A cannot reproduce its original value.

**Question:** should this diagnostic remain unauthenticated or acquire a new basis?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep an explicitly unauthenticated diagnostic | Mutation remains outside semantic verifier failure; do not imply event-derived time. | Disclosure only. |
| B. Replace/supplement it with a separately named event-derived diagnostic | Must define exact timestamp and versioned compatibility; changes the meaning, not proof of the old clock sample. | Deterministic operational metadata and replay comparison under a new contract. |
| C. Authenticate clock samples using an independent trusted record | Adds source, identity/order, durability, retention and recovery obligations. | Receipt-based diagnostic verification; no world-evidence authority. |

**Recommendation:** A unless an operational consumer justifies B/C. These are
diagnostic-policy choices, not repairs to accepted lineage. **Evidence required:**
flips/swaps, equal event times, copied stores and explicit inability to reconstruct
old samples from Layer A alone.

## W12. Legacy full-rebuild API and the crash-campaign boundary

**Source:** GAPS.md lines 462–481. `rebuild_projection(..., "0")` refuses;
legacy recovery uses `materialize_pending`. The recorded campaign's 280 kills
found no committed-event loss, partial publication or duplicate retry; that is
historical evidence, not a run performed for this packet.

**Question:** should legacy gain a full rebuild contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep the existing API boundary and explicit mid-rebuild test exclusion | No legacy snapshot adapter or promise to repair corrupt published legacy rows. | Continue supported pending publication; no new rebuild handler. |
| B. Define a dedicated legacy rebuild operation | Decide complete legacy-row/progress handling, evaluation T, original IDs, atomic replacement and corrupt-derived-state refusal/recovery. Freeze the old fold. | A separately accepted legacy rebuild API and actual mid-rebuild process-kill coverage. |
| C. Reconstruct only into a distinct recovery copy | Adds identity/bundle inventory, verification and operator adoption steps; avoids in-place replacement. | Explicit legacy recovery-copy tool after its contract is accepted. |

**Recommendation:** A for this scope; B only when full legacy repair is a stated
requirement. **Evidence required for B/C:** complete genesis equality at shared T,
corrupt derived input ignored, source preservation, reader isolation and kills
before/during/after replacement. Never remove the skip by inventing an adapter.

## W13. Strict duplicate-key payload admission

**Source:** GAPS.md lines 492–589. This is a decision-blocked hardening boundary,
not a demonstrated violation of the accepted canonical-content commitment.
Proposed [0036](../decisions/0036-strict-payload-keys.md) records C and the follow-up
answers, still unratified. Its shared schema bundle also requires Proposed 0037.

**Question:** ratify the prepared strict profile or choose another contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Diagnostic only | Reports repeated decoded keys read-only; no new admission guarantee. | A separately scoped diagnostic contract, not automatic permission to implement S7 today. |
| B. Tighten new admission under existing profiles | Changes an existing acceptance boundary without a recorded strict-history discriminator; needs explicit exception/amendments. | A revised admission-only contract and compatibility matrix. |
| C. Ratify prepared 0036 plus joint 0037 bundle | Recorded strict profile, recursive early refusal, old last-wins history/retries, raw-aware replay; permissive unique-key spelling and unchanged canonical hashes. | T1–T10 implementation after joint authority receipts and ordered dependencies. |
| D. Add original-text authentication | Requires new commitments, exact text identity, versioning and adoption proof; duplicate rejection alone supplies none. | A separately specified text-authentication protocol. |

**Recommendation:** C, as already ruled for drafting, without D. See the
[ratification packet](2026-10-15-ratification-packet-adr-0036-0037.md).
**Evidence required:** recursive escaped/equal keys, zero allocation/publication
on refusal, old exact retries, mixed raw histories and independent verifier rejection.

## W14. Cross-language canonicalization and verifier independence

**Source:** GAPS.md lines 591–658. Current Python defaults differ from Node's
number spelling; the independent Python/Node subset is bounded evidence, not a
production domain restriction. Proposed 0027 Gate 1/2 and
[B2's recorded rulings](0027-b2-private-value-codec-ruling-brief.md#rulings)
remain incomplete/unratified. The six MADE private-codec rulings already preserve
exact integers/binary64 distinctions, reject nonfinite values/duplicates/lone
surrogates, preserve Unicode and require canonical private input.

**Question:** which complete new codec/evidence contract should be submitted for review?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain current Python contract and limited assurance claims | Frozen hashes remain stable; portability and shared-parser limits stay disclosed. | Additional bounded evidence only; no new private codec or conformance claim. |
| B. Complete the current-compatible finite profile F1–F5 as a proposed new private codec | Confirm grammar/type/host adaptation, exact integer range, string/key lengths and units, depth/counting, document-size and capacity/refusal behavior; produce independent bytes and decoded-type/value vectors. | After completed Gate 1 evidence, independent Gate 2 review and explicit ratification: versioned codec/parser and conformance/verifier paths. |
| C. Explicitly reconsider JCS or another named new profile | Not a drop-in replacement: account for signed zero, integral floats, exact large integers and all six recorded rulings; explicitly amend incompatible choices. | A different versioned codec only after a complete replacement contract and compatibility evidence. |

**Recommendation:** develop B, retaining A's frozen runtime behavior. No safe-integer
bound, unlimited domain, incidental interpreter cap or object-key limit is selected
here. The evidence subset cannot settle those application choices. Private B2
canonical-input requirements and 0036's permissive plaintext spelling are distinct.
**Evidence required:** independent numeric/Unicode positive and negative vectors,
ambiguous-input refusal, runtime-version matrix, boundary/over-limit tests and
fault injection with shared production helpers disabled. Full codec independence
and cryptographic review remain separate from independent semantic reconstruction.

## W15. Timestamp representation after boundary refusal

**Source:** GAPS.md lines 680–698. Accepted
[0006](../decisions/0006-occurred-at-comparison-is-instant-based-not-lexical.md)
requires instant comparison; accepted spellings remain byte-identical. Offset-less
input refusal is resolved. This worksheet concerns the excluded representation
change, not a new claim of an ingestion defect.

**Question:** is one stored UTC spelling needed, or only a presentation convention?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Preserve storage spelling and instant comparison | Existing hashes, exact retries and provenance remain unchanged. | No normalization handler. |
| B. Add explicit display-only formatting | Define timezone/precision/unknown behavior while retaining original strings; display never feeds identity or hashing. | A bounded formatting/read adapter after its contract is accepted. |
| C. Introduce a new recorded normalized-input profile | Define original versus normalized fields, exact precision and retry identity; do not rewrite old events. | Versioned ingestion/compatibility handling and explicit copy adoption if required. |

**Recommendation:** A; B if consistent display is needed. C requires an actual
semantic requirement. **Evidence required:** Z/+00:00/non-UTC/fractional equivalents,
unchanged historical bytes and exact retry distinctions; no lexical time comparison.

## W16. Backdated corrections and external valid time

**Source:** GAPS.md lines 704–719. Accepted
[0005](../decisions/0005-backdated-corrections-fail-loud-pending-semantics.md)
keeps its interim refusal; [0034](../decisions/0034-forward-state-transitions.md)
retains the projector-3 target-event-time guard, equality allowed. External
validity is not supplied by a correction's recording position.

**Question:** should a later contract admit retrospective world-validity assertions?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain current backdated-correction refusal | Early corrections remain unsupported; accepted replacements/expiry keep their distinct meaning. | No new historical-validity operation. |
| B. Add explicit validity assertions, separate from event time | Define authority, valid intervals, knowledge cutoff and ambiguity as in W07; preserve frozen guards. | A new validity operation/read surface under an explicit contract. |
| C. Define a separately authorized backdated override | Must say what is overridden, for whom/when, and how knowledge-time history and no-promotion rules survive. | A specifically versioned override contract; no inferred general correction privilege. |

**Recommendation:** A until W07/B is complete, then B rather than overloading
`occurred_at`. **Evidence required:** earlier/equal/later target instants, late
arrival with earlier validity, cutoff before learning the correction and explicit
overlap/authority refusals. No current refusal is removed by this recommendation.

## W17. Origins beyond `observed`, including reported/model output

**Source:** GAPS.md lines 721–736 and 177–179. Accepted
[0001](../decisions/0001-observation-recorded-resolves-to-verified.md) maps observed;
[0031 section 2](../decisions/0031-source-report-claims.md#2-option-b-is-the-recorded-target)
leaves the future reported-origin name, state, event contract and projector open.
An artifact report's verified standing concerns what it stated, not embedded truth.

**Question:** which first additional origin/state contract should be specified?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep observed-only admission for supported value-setting paths | Unmapped origins keep explicit refusal; artifact reports retain their narrow accepted meaning. | No origin handler. |
| B. Specify the bounded reported-content origin first | Decide exact assertion scope, provenance, standing, evidence gates, retries and new selector/version; preserve option-(a) history. | A new report-origin producer/reducer/verifier contract. |
| C. Specify user-stated/preference and other origins together | Larger policy scope: user asserted X differs from X true, and preferences require explicit scope/authority. Model output cannot become observed by relabeling. | Only the individually ratified mappings and gates, never a blanket enum-to-state table. |

**Recommendation:** B before C; preserve A while undecided. **Evidence required:**
all-origin admission/refusal parity, unchanged old histories, user/world split and
no source-label promotion. Proposed Dream emissions in W23 have a permanently
distinct type under that proposal, not an origin shortcut into ClaimCandidates.

## W18. Remaining candidate corrections: report targets

**Source:** GAPS.md lines 738–786, especially 783–786. Ordinary projector-3
correction/replacement/expiry and dependency checks are implemented.
[0035 section 3](../decisions/0035-adr-0034-implementation-boundaries.md#3-report-corrections-deferred)
requires report-target transitions to refuse. Its deferred correction basis and
first extractor admission must be decided together; frozen `"1"`/`"2"` stay frozen.

**Question:** should report mis-extraction correction receive its first complete contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain report-transition refusal | New revisions/captures remain additional reports, not corrections. | No report correction handler. |
| B. Define one admitted mis-extraction correction | Specify basis and reviewed extractor together; require the same pinned source and location, an explicitly admitted extractor, and a different literal. Decide version/API guards and retries. | A narrow, independently reproducible report-correction producer and reducer/verifier path. |
| C. Seek broader source-revision replacement/expiry | Changes current report semantics and requires explicit supersession; revision changes must not silently invalidate immutable old reports. | Only a separately ratified broader lifecycle, with all provenance retained. |

**Recommendation:** A until a concrete mis-extraction need supports B. Do not
unblock all candidate corrections: most are already shipped, and report refusal
is deliberate. **Evidence required for B:** pinned bytes/location, admitted
extractor reproduction, mixed-target atomic refusal, frozen guards and exact retry
before checking now-ended targets.

## W19. Existing-subject association and multi-user authority

**Source:** GAPS.md lines 802–808 and 362–363. Accepted
[0019 section 4](../decisions/0019-identity-bootstrap.md#4-association-with-an-existing-subject-requires-an-admissible-basis)
requires a ratified admissible-basis list; accepted
[0020](../decisions/0020-multi-user-authority-undecided.md) separates attribution,
permission, intended reference and evidence, including with one operator.

**Question:** which authority scope should govern a recorded association?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Retain separate scoped subjects | Similarity, actor ID and speaker clarification authorize no shared-identity change. | No association handler. |
| B. Complete Proposed 0027's limited ledger capability/basis model | Record historical enrollment/grants and exact affected scope; permission remains distinct from relationship evidence. Close its independent protocol prerequisites. | After gates/ratification: the limited association/identity handlers under W01, not general ownership. |
| C. Specify multi-authority/contested participation first | Decide grant entitlement, ownership/consent disputes, per-user views and revocation with reproducible historical authorization. | The explicitly accepted broader authority/association surface; substantially larger scope. |

**Recommendation:** B only for the limited stage-three objective; keep A until
accepted. B's schema work does not require settling all C policies. **Evidence
required:** two speakers under one operator, scoped clarification, unauthorized
shared changes, permission without evidence and replay after later grant changes.

## W20. Mention correction

**Source:** GAPS.md lines 810–813. Accepted ADRs
[0019](../decisions/0019-identity-bootstrap.md) and
[0021](../decisions/0021-bootstrap-link-treatment.md) distinguish mention assertion
from property observation; candidate-correction mechanics do not apply automatically.

**Question:** how should a mistaken recorded mention be superseded?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Preserve immutable mentions and defer correction | Additional scoped records may exist but do not implicitly correct or reassign old support. | No mention-correction handler. |
| B. Define append-only mention supersession with an explicit scope | Decide text-extraction versus referent error, target/live eligibility, new IDs, authority and dependent claims/links. Refuse unsupported cascading effects. | A narrow mention-correction operation, history/read/replay contract and index updates. |
| C. Handle referent errors through a complete identity reinterpretation contract | Requires W01/W19/W25/W26 and exact support applicability; not a text-edit shortcut. | Explicit association/split/merge paths only within that ratified contract. |

**Recommendation:** prepare B for demonstrable extraction errors; retain A for
unresolved referent changes. **Evidence required:** original mention retained,
mention-only prefixes, dependent observations, invalid/colliding targets, retry,
cutoffs and no support reassignment or promotion by text correction.

## W21. Attaching support to an existing ClaimCandidate

**Source:** GAPS.md lines 815–819. Accepted
[0023 section 2](../decisions/0023-stage-two-contract.md#2-ordinary-observations-create-fresh-claimcandidates)
requires fresh candidates per observation. Accepted 0015's gate-approved
corroboration creates a new candidate; it does not compact contributors.

**Question:** is continuity worth introducing a separate support-attachment contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep fresh candidates per observation | Agreement does not imply identity; existing-ID reuse continues to refuse. | No attachment handler. |
| B. Define an explicit attachment event for established claim continuity | Decide target identity/applicability, evidence dedup, standing effects, dependency history at every cutoff, correction scope and retry identity. | A new versioned support-attachment reducer/read/verifier path. |
| C. Use separately gated corroboration instead of attachment | Preserve original candidates; new approved candidate has recorded dependencies and basis. Requires the unratified stage-three protocol. | After W01/gates: corroboration, not mutation of existing candidates. |

**Recommendation:** A until a continuity requirement justifies B; C addresses a
different evidence-assessment need. **Evidence required:** agreeing values with
different support, one event used through multiple paths, late attachment/correction,
all-cutoff lineage and no automatic promotion or duplicate evidence.

## W22. Usage recording and durable operational authority

**Source:** GAPS.md lines 836–843. Accepted
[0026](../decisions/0026-usage-is-not-evidence.md) excludes exposure/reference/activation
from belief evidence and lineage, but supplies no operational store.
[Temporal/activation direction](temporal-activation-direction.md#durable-activation-inputs-versus-invariant-8)
records the Invariant 8 tension rather than resolving it.

**Question:** what operational durability/replay promise, if any, is required?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep usage recording unimplemented | No durable usage history or feedback replay claim. | No recorder. |
| B. Specify session-only, explicitly lossy usage | Decide reset/retry/order/scope semantics and loss disclosure; no reproducible long-term history is promised. | A bounded ephemeral consumer after an accepted contract, never a world-event recorder. |
| C. Specify a separately authoritative durable operational log | Explicitly resolve Invariant 8, identity/order, retention, configuration versions, crash/restore and replay. It cannot be inferred from mutable process traces. | A usage recorder, recovery and deterministic activation-input replay outside belief evidence. |

**Recommendation:** C's specification work if persistent activation is intended;
A until authority is accepted. B is viable only with an explicitly disposable
product promise. **Evidence required:** generated/exposed/referenced distinctions,
duplicate retries, crash loss/recovery, config replay and unchanged belief
count/support/standing/lineage under repeated use.

## W23. Dream emission operations: eight separate worksheets

**Shared source:** GAPS.md lines 845–888; Proposed
[0029](../decisions/0029-dream-emission-semantics.md#remaining-unresolved-questions)
is unratified, Implementation: None. Its recorded direction is distinct emissions,
inseparable recall origin, no promotion to evidence and no causal-provenance
handle for activation scoring or Dream salience. Accepted 0026 already binds
usage separation. No option below promotes an emission or supplies hidden mutable
inputs to belief replay. Each subsection has its own unselected choices.

### W23.1. Emission recording and durability

**Source:** GAPS.md lines 856–858. **Question:** which store/persistence promise
should retain emissions while explicitly resolving Invariant 8?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Defer retained-emission functionality | No recall/history promise; do not imply an existing Dream subsystem. | No emission recorder. |
| B. Define mutable process history with explicit retention and loss semantics | Decide identities, order/retries, durable inputs, mutation audit and recovery; architecture's process traces are only a precedent. | A separate origin-preserving history/recall store after authority acceptance. |
| C. Define append-only emission history outside Layer A | Stronger retention burden and new durable authority/erasure tension; append-only policy must be explicit. | A distinct operational log, backup/restore and recall contract after ratification. |

**Recommendation:** B as the smaller candidate to specify; A remains runtime
scope until that decision. **Evidence required:** uncertain acknowledgment,
origin-preserving recall, crash/restore, intentional retention loss and no Layer A
emission append. Neither B nor C borrows the proposed erasure-witness exception.

### W23.2. Process-history replay and verification

**Source:** GAPS.md lines 859–861. **Question:** what does a history verification
operation establish independently of model regeneration?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Exact stored recall only | Return retained output/origin with explicit availability limits; do not claim complete history verification. | A recall reader after W23.1's contract. |
| B. Verify recorded history identity/order/completeness and causal records | Define authoritative inputs, integrity/semantic checks and completeness boundary. It cannot prove world truth. | An independent operational-history verifier/reconstructor with typed unavailable checks. |
| C. Also reproduce generation experiments | Requires model/build/config/seed/runtime inputs and an honest nondeterminism domain; regeneration is not the history oracle. | A separately labeled experiment tool alongside A/B, never evidence verification. |

**Recommendation:** B with exact recall separated from regeneration. **Evidence
required:** missing/extra/reordered records, wrong origin, partial retention and
unchanged world replay with the model disabled. A matching digest alone proves
neither complete history nor a proposition's truth.

### W23.3. Acquisition linkage and counting restrictions

**Source:** GAPS.md lines 862–865. **Question:** where should a check's initiating
emission be recorded, and can that relationship restrict evidence counting?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Defer causal linkage and dependent counting behavior | No claim of independent sources from absent links; acquisition still needs its independently admitted observation contract. | No causal-counting handler. |
| B. Define a verified process-only relation for explanation | Decide relation identity, source/destination typing, authority and missing-link meaning; it never becomes a reducer input. | Operational acquisition provenance with no belief-affecting counting rule. |
| C. Also define a replayable Layer A representation for subtractive restrictions | Must specify admissible relation/attestation, authority, verification, complete lineage and deterministic counting; process provenance can never create support. | A separately ratified counting-restriction path, plus B's provenance. |

**Recommendation:** B first; C only for an actual counting requirement and a
complete Layer A contract. **Evidence required:** repeated acquisition paths to
one observation, absent-link ambiguity, independent accepted observations and
no constitutive-link reuse, support creation or mutable-store hidden input.

### W23.4. Emission redaction and unavailable recall

**Source:** GAPS.md lines 866–869. **Question:** how can recall preserve origin
and necessary counting restrictions after protected emission content is unavailable?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Defer protected emission retention | Stay within public-only scope; no deletion/erasure claim. | No protected emission reader or erasure path. |
| B. Specify emission units and safe opaque residual records | Decide private dependencies, managed copies, origin-preserving unavailable results and restriction survival under Proposed 0028. | After both complete accepted contracts/gates: registered derivatives, erasure integration and typed recall. |
| C. Minimize retained text and keep only explicitly specified safe metadata | Less recall utility; metadata/topology can still reveal protected information and needs classification. | A narrower operational retention/availability policy after its own review. |

**Recommendation:** B's specification with minimization where justified; A until
R4 and all prerequisites pass. **Evidence required:** outputs/caches/backups in
closure, no content resurrection, origin retained and no loss of a restriction
that would manufacture independent support. A redacted ClaimCandidate is not a
substitute emission type.

### W23.5. Retrieval/activation feedback

**Source:** GAPS.md lines 870–874. **Question:** what reinforcement, if any,
should generated/exposed/referenced usage cause?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep a baseline with no activation feedback | No history-driven reinforcement or implied scorer. | No feedback implementation. |
| B. Specify observation-only usage instrumentation before ranking changes | Decide timing/dedup, scope/credit, cross-component accounting, candidate bias and underexposed evidence access. | After W22: measurable retrieval usage and controlled baseline evaluation. |
| C. Add a bounded versioned feedback policy after B | Requires explicit update rules, windows/limits and acceptance criteria; top-k eligibility does not guarantee exposure. | Evaluated activation ranking under its ratified policy; no evidence/standing changes. |

**Recommendation:** B before C, using A as baseline. **Evidence required:** paired
closed-loop trajectories, retries/pagination/topic changes, duplicate material and
late counterevidence; report concentration/recall separately. Scorer and salience
receive no causal-provenance handle through logs, metrics or caches.

### W23.6. Dream instrumentation

**Source:** GAPS.md lines 875–878. **Question:** which operational definitions
make Generative Flux, raw emission count N and Inquiry Yield reproducible?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Defer the metrics | No denominator/window or claimed yield result. | No metric consumer. |
| B. Specify complete raw instrumentation first | Define attempted cycles, R_opportunity/R_zero, non-deduplicated N, windows, units, missing data and Inquiry Yield; preserve pre-governance measurement. | A versioned collector/report after recording authority is settled. |
| C. Add metric-driven scheduling after B | Requires a separate consumer/control contract and evidence that accuracy pressure does not suppress generation before measurement. | Only the explicitly accepted operational control loop. |

**Recommendation:** B, without C initially. No formula or numerical default is
selected here. **Evidence required:** zero-opportunity versus zero-output cycles,
repeated identical emissions counted in N, interrupted attempts, governed-away
outputs still counted and reproducible reports over retained operational inputs.

### W23.7. Question/open-inquiry lifecycle

**Source:** GAPS.md lines 879–882. **Question:** what obligation survives an
insufficient-evidence result, and how can it close or expire?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep inquiries session-local with no durable obligation | Explicitly disclose loss at session end; no recovered work queue claim. | A bounded ephemeral inquiry surface after its semantics are accepted. |
| B. Define durable operational inquiry records | Specify exact scope, identity/retries, closure/expiry/indexing, owner/configuration and recovery; resolve sole-copy authority under Invariant 8. | A retained inquiry lifecycle/index and recovery path, separately from world beliefs. |
| C. Keep durable inquiries but require explicit closure | Avoid automatic expiry decisions at first, while still defining cancellation/retention and recovery. | A narrower B contract with explicit terminal actions. |

**Recommendation:** C for the first durable candidate; decide expiry explicitly
before adding it. **Evidence required:** retrieval-to-answer, acquisition-to-answer
and insufficient-evidence branches stay distinct; retries/crashes create no lost
or duplicate obligations, and acquisition success does not imply inquiry closure.

### W23.8. Spleen Dream yield

**Source:** GAPS.md lines 883–885. **Question:** is this a health report, a
separate metric or a control signal, and how does it relate to Inquiry Yield?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Defer the named metric | Architecture's name supplies no calculation or implementation. | No Spleen Dream-yield handler. |
| B. Define a reporting-only health measure with an explicit relationship to Inquiry Yield | Decide inputs, units/window, missing-data behavior and consumer permissions; avoid duplicate inconsistent definitions. | A reproducible health report after W23.6 and its recording contract. |
| C. Also make it a scheduling/control input | Needs an independently ratified feedback contract and forbidden-input audit. | Only the approved control path; never a causal-provenance handle for salience. |

**Recommendation:** B after instrumentation, without C. **Evidence required:**
known-input calculations, empty/partial windows, configuration replay and a
consumer/input inventory proving the reporting path cannot reopen excluded
causal provenance or change support/verification.

## W24. Additional scalar belief reads

**Source:** GAPS.md lines 890–895. Accepted
[0024 section 2](../decisions/0024-no-authoritative-head.md#2-scalar-belief-requests-and-named-candidate-reads)
defers common-value reads; the code also supplies no single-candidate scalar
belief contract. Named-candidate reads already work.

**Question:** should callers get another scalar convenience operation?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep named-candidate/set reads only | Caller names the claim; no belief-level scalar implication. | No new scalar API. |
| B. Define an explicit exactly-one-eligible-candidate read | Decide eligibility for live/retained candidates, equality domain, unknown/zero/multiple outcomes, time/version and provenance disclosure. | A separately named read operation after acceptance, with no authoritative head. |
| C. Define an agreeing-common-value read | Must specify exact value equality and ambiguity/standing disclosure; agreeing candidates remain distinct with all support. | A new common-value read contract, never coalescing or pooled verification. |

**Recommendation:** A unless callers need B; consider C separately. **Evidence
required:** zero/one/multiple candidates, equal values with different standing,
retained candidates, cutoffs and byte-identical lineage before/after repeated reads.

## W25. Non-constitutive link treatment

**Source:** GAPS.md lines 897–902. Accepted
[0021 section 3](../decisions/0021-bootstrap-link-treatment.md#3-confidence-ceiling-computation)
excludes constitutive links from scoring, but does not assign scores or treatment
to other link kinds. Missing treatment must not be silently excluded from a path.

**Question:** what first later-link treatment should receive a complete contract?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep constitutive-only paths and refuse unspecified links | No invented score, empty minimum or resolved-identity inference. | No new link reducer. |
| B. Define an explicitly unscored structural later-link kind | Must justify its semantics/applicability, authority, transitions and effect on candidate paths; unscored is an explicit decision. | A narrow versioned link/association/read path after W19 as applicable. |
| C. Define scored matching links and path ceilings | Decide score meaning, evidence/authority, multi-hop composition, unresolved paths and changes over time; do not turn confidence into evidence. | A scored-link contract and deterministic path evaluation, without automatic promotion. |

**Recommendation:** A until a real link use case determines B or C. **Evidence
required:** mixed constitutive/later paths, unresolved required links, no numeric
bootstrap stand-in and equivalent results across identity paths. The old legacy
minimum formula alone does not settle applicability or the broader link lifecycle.

## W26. Support-dependent demotion and restoration

**Source:** GAPS.md lines 897–902; ordinary-transition dependency refusal is
already implemented at 759–770. Accepted
[0015 section 5](../decisions/0015-candidate-scoped-verification.md#5-restrictions-follow-actual-dependencies)
requires restrictions to follow actual justification, without inventing blanket
demotion destinations or restoration rules. Accepted 0035's predicate stays in force.

**Question:** which dependency/standing transitions should be specified first?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep present unsupported-dependency refusals | No candidate remains verified on a failed necessary justification by an invented fallback. | No dependent-standing handler. |
| B. Define a finite dependency-trigger/destination matrix | Specify usable support, necessary versus alternative justifications, recorded causes, time/cutoff and every hold/demotion outcome; unspecified rows still refuse. | Bounded deterministic restriction/demotion handlers and independent replay checks. |
| C. Add restoration plus separate gated re-verification to B | Define usable surviving justification and approval history; removing adverse evidence is not promotion authority. | Only the explicitly ratified restoration/re-verification operations. |

**Recommendation:** B before C, leaving A outside the completed matrix. **Evidence
required:** dependent/unrelated claims, alternative support, quarantined necessary
evidence, merge/split/remerge round trips and no promotion after erasure or removal
of restrictions. Do not weaken the shipped predicate before replacement authority.

## W27. Idempotency key and event-type separation

**Source:** GAPS.md lines 915–920. Accepted
[0003](../decisions/0003-genesis-sentinels-and-hash-material-delimiters.md),
[0004](../decisions/0004-correction-appended-supersedes-via-superseding-events.md)
and [0030](../decisions/0030-sole-writer-and-positional-fields.md) fix the formula
and semantic collision refusal. This is a noted design boundary, not an open bug.

**Question:** must otherwise equal source/time/payload submissions of different
event types ever coexist?

| Unselected option | Consequences | Implementation unlocked |
|---|---|---|
| A. Keep the accepted key and conflicting-semantic refusal | Existing retry identity and frozen hashes remain intact. | No formula change. |
| B. Define a new explicitly recorded idempotency profile including event type | Requires complete version/dispatch/uniqueness, mixed-history lookup and original-pair retry rules; old keys are never rewritten. | New-profile admission/retry handling under separate authority. |
| C. Define a distinct operation identity independent of the existing key | Larger API/storage/commitment design; cannot simply bypass the current uniqueness rule. | Only a newly ratified operation/retry protocol with explicit compatibility. |

**Recommendation:** A until an actual coexistence requirement exists. **Evidence
required for B/C:** same semantic retry returns original pair, cross-type conflict
versus allowed coexistence, config-only conflicts, uncertain acknowledgment and
unchanged old hashes. Reminting IDs or bypassing uniqueness is not a resolution.

## Ruling and implementation handoff

Josh may record worksheet choices individually; a choice is not ratification of
every recommendation in this packet. A response must identify the worksheet and
option, the required complete contract and bounded refusal domain, then follow
[AGENTS.md's authority protocol](../AGENTS.md#adr-commit-protocol). Agents never
set the authority environment variable or commit protected records. Authority,
implementation and completion-marker commits stay separate, one ADR at a time.

0036/0037 need the formal action in their
[ratification packet](2026-10-15-ratification-packet-adr-0036-0037.md); they have no
remaining drafting questions. Other worksheets remain recommendations with
unresolved choices/mechanics. No “all recommended” answer for those two proposals
applies to W01–W27 by association. Existing 0027/0028/0029 Proposed statuses and
all gap statuses are unchanged. Full-suite/checker evidence for this documents-only
commit is retained in the worktree's ignored `scratch/EVIDENCE.md`.
