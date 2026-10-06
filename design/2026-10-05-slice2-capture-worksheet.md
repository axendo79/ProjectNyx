<!-- Drafted by the Dot (Task C, 2026-10-05) from main 5313653; reviewed and placed by Claude. Non-authoritative. -->

# Public web and PDF captured bytes decision worksheet

**Status:** NONAUTHORITATIVE Task C draft. Every option remains unselected. This worksheet supplies no ratification, implementation authority, defaults, property names or origin mapping. Required implementation and acceptance tests below are conditional future work, not completed work.

**Source baseline:** [axendo79/ProjectNyx at `5313653ebfebf9f54946f4f495d522d773e2c3d8`](https://github.com/axendo79/ProjectNyx/tree/5313653ebfebf9f54946f4f495d522d773e2c3d8), read 2026-10-05. All ADR section/line citations refer to this pin. Read AGENTS.md, README and applicable accepted ADRs before using specification mechanics. Both requested style worksheets exist: `design/2026-10-04-supersession-worksheet.md` and `design/2026-10-03-adr-0031-worksheet.md`. Their historical statuses/options do not override subsequent acceptance.

[ADR 0031](https://github.com/axendo79/ProjectNyx/blob/5313653ebfebf9f54946f4f495d522d773e2c3d8/decisions/0031-source-report-claims.md#L3-L9)'s Status/Implementation markers say accepted, slice 1 complete, slice 1b deferred. Its body contains older “Implementation remains None” statements; those are not current status. README's public-report section describes only pinned ADR literals. Slice 2 has no complete public-web/PDF contract here.

## C1 Capture claim meaning

**Exact open choice:** Which narrowly defined statement about a captured artifact becomes a claim?

**Unselected options:**
- [ ] An exact quoted statement located in an identified capture.
- [ ] A named literal field extracted under a bounded document grammar.

**Accepted constraints:** ADR 0031 §1, lines 47–73, verifies only what an identified artifact contained in its recorded context. It verifies neither the embedded proposition, author authority, faithful extraction by assumption, nor source independence. A property suffix supplies no report meaning.

**Required implementation:** Ratify each exact property, subject scope, value shape, verifiability and supported document class. Define absence, ambiguous matches and extraction failure without fabricating values. Reader wording must identify the capture and qualify verification accordingly.

**Acceptance tests:** False embedded proposition remains only a report; missing field produces no fabricated claim; ambiguous extraction follows the ratified refusal; title/author assertions gain no institutional authority.

## C2 Capture identity and URL provenance

**Exact open choice:** What exact byte representation and acquisition record identify the capture?

**Unselected options:**
- [ ] Retain one specified response-body representation plus its capture manifest.
- [ ] Retain transport/content-encoded and decoded representations with an explicit transformation manifest.

**Accepted constraints:** ADR 0031 §§1, 8(a), lines 47–65, 334–340, requires identified artifacts and exact locations; its repository/path/revision/blob descriptor is a first-slice contract, not an HTTP schema. ADR 0030 §2 treats full source.config as immutable semantic provenance.

**Required implementation:** Specify requested URL, ordered redirect chain and final URL, request/response metadata relevant to representation, status/media type, byte boundary, digest algorithm/domain, byte length, immutable storage reference and acquisition evidence. Distinguish byte identity from acquisition identity. Decide URL spelling/normalization and query/fragment treatment explicitly; neither URL equality, redirect nor digest equality establishes subject equivalence. A digest binds retained bytes, not server authorship or retrieval time.

**Acceptance tests:** Same URL/different bytes; same bytes/different URLs or captures; redirect loop/changed destination; encoding variants; digest/length mismatch; missing retained object; replay without network.

## C3 Times and bounded capture

**Exact open choice:** Which timestamp supplies occurred_at, and which capture/resource limits define admissibility?

**Unselected options:**
- [ ] Capture-time occurred_at, with import time separately recorded.
- [ ] Import-time occurred_at, with acquisition times separately recorded.
- [ ] One ratified limit profile for admitted formats.
- [ ] Separately versioned HTML/PDF limit profiles.

**Accepted constraints:** ADR 0006 Decision, lines 46–59, requires offset-bearing instants and preserved spellings. ADR 0030 §§2, 6 reserves recorded_at for the writer and supplies no historical override. ADR 0031 §8(f), lines 617–625, selects import time for slice 1 only.

**Required implementation:** Specify start/completion meaning, retained source-date/header text, clock-failure handling, limits on encoded/decoded bytes, redirects, duration, PDF pages and extraction expansion. Select exact thresholds and outcomes; no numbers are supplied here. Define partial/truncated-response treatment before claim preparation.

**Acceptance tests:** Equivalent timezone spellings; source date never substitutes for recorded_at; delayed import; missing offset; boundary and over-limit inputs; decompression expansion and interrupted downloads cannot silently appear complete.

## C4 Quotes and extraction verification

**Exact open choice:** Which deterministic extraction and location model supports each admitted format?

**Unselected options:**
- [ ] Literal text directly addressable in an explicitly decoded text artifact.
- [ ] HTML/PDF extraction into a retained, versioned text representation with a defined source-location mapping.
- [ ] Defer OCR-only documents.
- [ ] Seek a separate bounded OCR extraction/admission contract.

**Accepted constraints:** ADR 0031 §3, lines 124–145, separates faithful extraction, writer enforcement and replay integrity; §8(f)'s UTF-8 Markdown grammar does not authorize HTML/PDF extraction.

**Required implementation:** Pin extractor identifier/version, configuration, input digest, output bytes/digest, decoding/normalization rules and location coordinates. Define quote equality, ordering, repeated matches, ligatures, hyphenation, columns and missing text. PDF decoded-text offsets are not raw PDF byte offsets; page coordinates alone are not byte proof. Define how independent verification reproduces the quote and mapping from retained input. Rendering or OCR needs its own recorded interpretation and refusal domain.

**Acceptance tests:** Exact quoted-text equality in its declared representation; raw-input digest check; compressed PDF text; duplicate quotation; reordered columns; parser-version/config drift; corrupt file; non-reproducible extraction refuses. Replay consumes recorded events, never reruns extraction.

## C5 Vocabulary mechanism

**Exact open choice:** How is the new reviewed vocabulary/extraction contract represented without treating slice 1's closed ADR schema as generic?

**Unselected options:**
- [ ] Reuse the producer-generic declaration/admission mechanism with explicitly ratified finite web/PDF definitions and schema extensions.
- [ ] Propose a different mechanism with the necessary explicit amendments and compatibility contract.

**Accepted constraints:** ADR 0031 §§3–4, 8(a–c), and lines 715–720 bind complete definition hashing, reviewed immutable identity/version/hash combinations, exact property strings and retained historical definitions. Slice 1 admits only three ADR literal combinations (§8(b), lines 379–428). Later producers need complete reviewed meanings, scopes, shapes and extraction contracts.

**Required implementation:** Specify exact closed definitions, supported tags, canonical set/sequence treatment, declaration compatibility and any necessary versioning. Preserve existing vocabulary bindings and canonical hashes. Reuse is not permission to invent entries, silently expand the old definition, or admit caller-generated hashes.

**Acceptance tests:** Unknown property/shape/scope refuses; definition tampering changes digest; identity/version rebinding refuses; retired histories replay unchanged; old schema fixtures remain valid; each new contract has reviewed canonical fixtures.

## C6 Subjects and mentions

**Exact open choice:** What does a mention refer to across successive captures?

**Unselected options:**
- [ ] A capture-specific artifact, bootstrapped separately for each distinct acquisition.
- [ ] A precisely defined resource scope spanning captures, reused only through retained mention/subject associations.

**Accepted constraints:** ADR 0019 §§1–4, 6 requires separate scoped bootstrap and recorded identities, without matching; ADR 0021 §§1–2 makes the link constitutive without confidence. ADR 0022 §§1–2 requires one current belief per exact subject/property pair. ADR 0031 §8(e)'s repository-qualified path formula does not define web identity.

**Required implementation:** Ratify scope representation and acquisition/resource distinction. Persist associations before submission; later observations name recorded mentions. A new mention cannot silently attach to an existing subject. Redirect, canonical-link, title, URL similarity or identical bytes supplies no admitted association basis.

**Acceptance tests:** Mention-only prefix has no property claim; missing association refuses; duplicate current belief refuses without redirection; similar URLs and matching PDF titles remain unmerged; retry/replay preserves IDs.

## C7 Recapture and changed reports

**Exact open choice:** When does a requested recapture constitute a new acquisition observation rather than resumption of a saved request?

**Unselected options:**
- [ ] Every explicitly initiated, successfully completed acquisition can produce new reports with their own acquisition provenance, including unchanged content.
- [ ] A defined capture ledger reuses already retained acquisitions; only separately established new acquisition units can produce new reports.

**Accepted constraints:** ADR 0031 §1, lines 70–73, and ADR 0024 §§1–3 retain differing and agreeing candidates without a winner. ADR 0023 §2 requires fresh candidates for genuinely new observations; ADR 0030 §3 returns the original pair for equivalent committed retries. ADR 0026 Decision excludes retrieval usage from evidence.

**Required implementation:** Define acquisition identity, completion/resumption and scheduling boundaries. Changed bytes at a URL create another report under the selected scope, never an automatic correction. Do not treat cached retrieval, repeated display or digest equality as new independent corroboration.

**Acceptance tests:** Interrupted capture/import resumes without duplicate evidence; same saved request appends nothing; changed content retains both reports; unchanged recapture gains no inferred independence; no latest-value head.

## C8 Storage and backup

**Exact open choice:** Where are source bytes and extraction artifacts durably retained?

**Unselected options:**
- [ ] A versioned beside-store, content-addressed capture bundle committed by recorded digests.
- [ ] A ratified database-contained representation with explicit format/schema compatibility.

**Accepted constraints:** ADR 0030 §§1–3 requires caller request retention and preserves separate append/publication transactions. ADR 0031 §8(e–f) and Acceptance cases, line 795, requires durable saved requests, preserved definitions/bindings, software/policy revisions and a consistent SQLite backup. ADR 0025 §§1, 3, 5–6 preserves historical bytes and complete logical provenance.

**Required implementation:** Define persistence-before-admission ordering, manifest/object consistency, immutable references, corruption behavior and recovery of orphaned/pending captures. Inventory raw bytes, decoded text, mappings, metadata, requests, caches, WAL and backups. Specify backup/restore closure; neither a URL nor digest replaces retained source bytes. No garbage-collection default is supplied.

**Acceptance tests:** Crash at each persistence/append/publication boundary; missing/corrupt object; offline restore reproduces capture and extraction evidence; saved requests resume unchanged; publication reaches exact log tip. Reject backup claims based only on copying an active SQLite main file.

## C9 Writer admission and public-only policy

**Exact open choice:** How are reviewed public acquisitions and their producer bound to the existing trusted admission boundary?

**Unselected options:**
- [ ] Pre-reviewed immutable capture manifests admitted by exact identity.
- [ ] A ratified public-acquisition policy admitting bounded captures after complete validation.

**Accepted constraints:** ADR 0031 §§3–4, 8(c–d) requires writer-owned classification on every producer-accessible route, immutable startup policy, committed-retry comparison before new admission, and no policy check during replay. Its Git-tree allowlist is not a web allowlist. §7, lines 284–315, keeps public-only policy until erasure requirements are accepted, implemented and passed.

**Required implementation:** Define trusted producer binding, public-input review, redirect/destination restrictions and startup validation. Cover authenticated/personalized responses, credential-bearing URLs, private-network destinations, protected PDFs and accidentally captured private material; specify refusal before persistence/admission as applicable. Public accessibility alone is insufficient review. Record no privacy, deletion or secure-erasure guarantee.

**Acceptance tests:** Private input and public-to-private redirect refuse; omitted declaration, changed actor/source labels and alternate routes cannot bypass admission. Running policy is immutable; retirement rejects uncommitted requests but preserves exact committed retries. Replay success never certifies admission.

## C10 Projectors and report corrections

**Exact open choice:** Which report import/read surfaces will support the new contract, while report corrections remain deferred?

**Unselected options:**
- [ ] Specify the slice using explicitly selected supported "1"/"2" report surfaces.
- [ ] Seek an explicit extension of report import/read support to "3", preserving report-transition refusals.
- [ ] Defer report-correction work entirely.
- [ ] Prepare a separate future report-correction decision without enabling it here.

**Accepted constraints:** ADR 0032 Decision prohibits defaults/upgrades. ADR 0031 §8(d,g) limits its importer/adapter to "1"/"2". ADR 0034 §§1, 5–6 supplies projector "3" ordinary transitions and distinguishes immutable revision reports. **[ADR 0035 §3, lines 86–96](https://github.com/axendo79/ProjectNyx/blob/5313653ebfebf9f54946f4f495d522d773e2c3d8/decisions/0035-adr-0034-implementation-boundaries.md#L86-L96) supersedes the report mis-extraction route by deferring it: all report-target corrections refuse at append and replay; replacement/expiry also refuse.** Its report marker is recorded source.config.report_vocabulary.

**Required implementation:** Specify supported surfaces/version isolation. Future correction work must decide the basis shape and first extractor admission together, preserving ADR 0034's four conditions: same pinned source, same location, explicitly admitted extractor, different literal. Web/PDF equivalents of repository/path/revision/blob require an explicit scope decision; a digest is no automatic substitute. A newer extractor is not inherently more truthful.

**Acceptance tests:** Every report transition refuses unchanged under current authority; changed capture is never targeted as correction; frozen versions remain reproducible. Any separately ratified future correction needs admission/reproduction evidence, dependency checks, retained history and equality at shared time/cutoff/version.

## Downstream dependency accounting

- Capture/import and report-detail delivery depend on C1–C6, C8–C10; repeated operation additionally requires C7.
- Offline audit and reproducible quotation depend on C2–C4/C8. Integrity-only verification cannot substitute for capture/extraction evidence.
- Resource-spanning comparisons require C6/C7; recency, redirects and equal values resolve no identity or truth.
- Report-correction consumers remain blocked by ADR 0035 until a separate complete decision; public-document admission alone does not unblock them.
- Model-generated summaries and the future origin name/state/event/projector mapping remain undecided and unauthorized (ADR 0031 §2 and lines 749, 763–765). Topic selection, retrieval, Dream references and repeated use remain usage, never evidence or lineage; no usage recorder is authorized (ADR 0026).
- Listing/indexing, protected storage and world-validity semantics remain separate work.

**Resolver and finish condition:** The maintainer records explicit choices, bounded refusals and necessary authority amendments. Implementation follows only the confirmed authority commit under AGENTS.md's A/B protocol, with independent acceptance evidence. This draft selects nothing and reports no implementation or test execution.