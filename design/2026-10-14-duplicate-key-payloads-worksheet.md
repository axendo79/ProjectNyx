# Duplicate-key payload text: decision worksheet

**Status: Non-authoritative design draft.** Prepared 2026-10-14 against
`5acc188` on `main`, using Python 3.14.2. This worksheet records observations,
options and a recommendation. It ratifies no decision, changes no acceptance
boundary and authorizes no implementation.

The decision concerns [the duplicate-key GAPS entry](../GAPS.md#duplicate-key-payload-text-is-accepted-outside-canonical-writer-preparation).
It is hardening requiring a ruling, not a demonstrated violation of the accepted
canonical-content commitment. Implementation remains blocked until the maintainer
records an accepted contract through [the authority protocol](../AGENTS.md#adr-commit-protocol).

## 1. Decision in one paragraph

Should future submissions reject repeated decoded object keys, and at which
version/admission boundary, while retaining the interpretation of already
committed histories? A second, separate choice is whether Nyx should authenticate
original payload text. Duplicate rejection alone supplies no original-text
commitment: whitespace, escape spelling and member order can still differ while
decoded canonical content is identical. Neither choice is supplied by this draft.

## 2. Exact current behavior and evidence

Line references below are to the baseline above. They deliberately refresh the
older line numbers and counts in GAPS and the
draft [B2 brief](0027-b2-private-value-codec-ruling-brief.md#2-complete-call-site-inventory-and-external-payload-reachability).
That brief is non-authoritative. Its recorded MADE rulings concern a **new private
codec**, retain frozen old parsing and do not ratify the draft.
Proposed [ADR 0027](../decisions/0027-stage-three-authority-and-acceptance.md) remains unratified.

| Boundary | Observed behavior and file:line evidence |
|---|---|
| Canonical preparation | [events.py:115-118,148](../src/nyx/events.py) and [writer.py:53-61](../src/nyx/writer.py) serialize an already constructed mapping. The output has one member per mapping key; preparation cannot recover duplicate members already lost upstream. |
| Shared serializer | [hashing.py:24-30,65-85](../src/nyx/hashing.py) sorts object keys, uses compact separators, preserves Unicode, and hashes UTF-8 canonical content. It uses the existing Python number encoder. The envelope includes the canonical payload hash. |
| Raw payload decoding | [integrity.py:51-58,100-122](../src/nyx/integrity.py) calls default `json.loads`, requires an object, and recomputes payload/idempotency commitments from the decoded object. It does **not** compare the submitted payload text with its canonical encoding or reject duplicate keys. Last occurrence wins recursively within each object. |
| Ordinary semantic requests | [writer.py:39-44,64-97](../src/nyx/writer.py) accepts caller-authored `PayloadRequest.ciphertext`, decodes it with default `json.loads`, assigns commitments to decoded canonical content and retains the supplied text. The dataclass is no proof of encoder provenance. [storage.py:385-444](../src/nyx/storage.py) commits these requests; [ingestion.py:54-65](../src/nyx/ingestion.py) wraps append and publication. |
| Retained-pair appends | [storage.py:314-369,495-525](../src/nyx/storage.py) accepts caller-supplied `Envelope`/`Payload`, validates decoded contents and stores `payload.ciphertext` itself. Both legacy and stage-two paths are reachable through Python APIs. No SQL bypass is needed for the reproduction. |
| Reads and replay | [storage.py:548-575,907-934](../src/nyx/storage.py) decodes stored Layer A content for reads, pending publication and explicit replay. [reducer.py:190-192](../src/nyx/reducer.py) and [committed.py:198-204](../src/nyx/committed.py) put decoded payload content, rather than its original text, into dependencies. |
| Standalone verifier | [verify_store.py:83-153](../scripts/verify_store.py), especially 130-145, independently reads raw payload rows but uses default `json.loads` and the shared canonical serializer/hash primitives. Reconstruction independence is not parser independence or proof of original-text authentication. |
| Committed retries | [writer.py:46-50](../src/nyx/writer.py) includes ciphertext text in semantic contents. [storage.py:406-412,447-483](../src/nyx/storage.py) compares retained requests/pairs; equal decoded content with different text is not an equivalent retry. |
| Merkle nodes | [merkle.py:226-243](../src/nyx/merkle.py) and [verify_store.py:156-181](../scripts/verify_store.py) additionally require stored node text to equal canonical re-encoding. Acceptance of noncanonical **Layer A payload text** does not imply acceptance of noncanonical node bodies. |
| Strict policy files | [report_policy.py:25-46,253-272](../src/nyx/report_policy.py) already rejects duplicate decoded keys for policy/definition input. This is a separate admission-file parser; it is not called by the shared raw payload decoder and does not make historical payload parsing strict. |
| User-facing reachability | [cli.py:33-52,69-125](../src/nyx/cli.py) implements read-only inspection, without a payload-submission command. The demonstrated route is a Python application supplying text to the append APIs; it is not evidence of a public network ingestion endpoint. |

### Current decoder recount

An AST walk of every Python file under `src/nyx/`, plus
`scripts/verify_store.py`, finds **44 `json.loads` calls: 43 without keywords and
one with hooks**. Count calls rather than lines; `storage.py:606` has two calls.
The sole hooked call is `report_policy.py:38-40` (`object_pairs_hook`,
`parse_float`, `parse_constant`; no `parse_int`). The raw payload paths remain
permissive. GAPS' 35-call statement and B2's earlier 31-call inventory are dated
evidence, not the current total. No existing document is changed by this worksheet.

Recount from the checkout root:

```python
import ast
from pathlib import Path

calls = []
for path in sorted(Path("src/nyx").glob("*.py")) + [Path("scripts/verify_store.py")]:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "json" and node.func.attr == "loads"):
            calls.append((str(path), node.lineno, [k.arg for k in node.keywords]))
print(len(calls), sum(not keywords for _, _, keywords in calls))  # 44, 43
print([call for call in calls if call[2]])
```

### Synthetic store results, 2026-10-14

Eight fresh temporary schema-5 stores were exercised, one for each combination
of projector `"0"`/`"1"`/`"2"`/`"3"` and retained-pair/ordinary-request route.
Each used fixed explicit IDs, public synthetic text, source actor `worksheet`,
source class `worksheet` and offset-bearing time `2026-10-14T12:00:00Z`.
Stage-two stores first committed and published a constitutive mention. The legacy
probe used **string** values, respecting ADR 0033; the older numeric append probe
is not a valid current legacy-admission example.

For each observation, preparation used value `"last"`. Before its first append,
only payload text was replaced with `"value":"first","value":"last"` at the
same object position. For stage two this is inside a member of `claims`.
Retained-pair commitments were left unchanged; ordinary requests let the writer
assign them. No validator, source file or Layer A table was edited.

| Projector | Retained pair: first append | Ordinary request: first append | Stored text / decoded value | Exact retry / changed-text retry | Verifier failures, log / full |
|---|---|---|---|---|---|
| `"0"` | `True` | committed pair returned | unchanged / `"last"` | no new append / `IntegrityError` | 0 / 0 on both stores |
| `"1"` | `True` | committed pair returned | unchanged / `"last"` | no new append / `IntegrityError` | 0 / 0 on both stores |
| `"2"` | `True` | committed pair returned | unchanged / `"last"` | no new append / `IntegrityError` | 0 / 0 on both stores |
| `"3"` | `True` | committed pair returned | unchanged / `"last"` | no new append / `IntegrityError` | 0 / 0 on both stores |

Checks included SQL text readback, `read_all_events`, explicit whole-view replay,
canonical versus raw-text digests, identical retries and a retry whose only change
was replacing duplicate text by its canonical single-key encoding. The verifier
was exercised through both `read_log` and `verify_store`, after publication.
Zero failures has the verifier's documented scope; it does not establish a strict
decoder contract or certify world truth. Temporary stores were removed on close.

Here is a compact reproduction of the ordinary-request half. Run the Python block
with `.venv/Scripts/python.exe` from the checkout root; it uses only temporary
stores. For the retained-pair half, construct the same payload with `build_event`,
replace the resulting `Payload.ciphertext` before its first append, and call
`safe_append_event(conn, *pair, version)` followed by `materialize_pending`.

```python
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import runpy
from nyx import events, hashing, storage, writer

at = "2026-10-14T12:00:00Z"
source = {"actor_id": "worksheet", "config": {}}
verify = runpy.run_path("scripts/verify_store.py")["verify_store"]
for version in ("0", "1", "2", "3"):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "probe.sqlite"
        with closing(storage.init_db(path, create=True)) as conn:
            conn.clock = lambda: at
            def prepare(kind, data, event_id):
                return writer.prepare_event(
                    event_type=kind, origin_type="observed", source=source,
                    source_class="worksheet", occurred_at=at, payload=data,
                    entity_refs=["s"], event_id=event_id)
            if version != "0":
                mention = prepare(events.ENTITY_MENTION_RECORDED, {
                    "mention_id": "m", "subject_id": "s", "text": "public example",
                    "link_state": "constitutive"}, "mention")
                storage.append_submission(conn, mention, version)
                storage.materialize_pending(conn, at, version)
            claim = {"belief_id": "b", "value": "last",
                     "verifiability": "externally_checkable"}
            if version != "0":
                claim.update(claim_candidate_id="c", mention_id="m",
                             subject_id="s", property_id="p")
            data = claim if version == "0" else {"claims": [claim]}
            request = prepare(events.OBSERVATION_RECORDED, data, "observation")
            raw = request[1].ciphertext.replace(
                '"value":"last"', '"value":"first","value":"last"')
            request = (request[0], replace(request[1], ciphertext=raw))
            pair = storage.append_submission(conn, request, version)
            storage.materialize_pending(conn, at, version)
            assert pair[1].ciphertext == raw
            assert storage.read_all_events(conn)[-1][1] == data
            assert hashing._sha256_hex(raw) != pair[0].payload_hash
            assert storage.append_submission(conn, request, version) == pair
        assert verify(path, version)["failures"] == []
        print(version, "accepted; raw text retained; verifier passed")
```

The minimal hash example is independent of event admissibility:

| Text | Raw UTF-8 SHA-256 | Nyx hash of decoded canonical content |
|---|---|---|
| `{"value":1,"value":2}` | `ef07538311c29ebdde0960d157b1222ff7f39622c0367ff23305a592d997dbda` | `49c987621f206f09e5fbe23b516b55a36f838cb14867961f1d84a554d3a35b6b` |
| `{"value":2}` | `49c987621f206f09e5fbe23b516b55a36f838cb14867961f1d84a554d3a35b6b` | `49c987621f206f09e5fbe23b516b55a36f838cb14867961f1d84a554d3a35b6b` |

Both decode to `{"value":2}`. This is loss of parser information, **not a hash
collision**. The current decoder also collapses `{"x":1,"\u0078":2}` to `{"x":2}`.
Composed `"\u00e9"` and decomposed `"e\u0301"` remain distinct decoded keys.
These observations establish Python behavior only, not another decoder's result.

## 3. Binding constraints and boundaries

| Accepted authority | Consequence for the ruling |
|---|---|
| [Architecture invariants 1,8,9,14](../spec/NYX_ARCHITECTURE.md#constitution-invariants-every-component-obeys), [executable replay invariant](../spec/NYX_ARCHITECTURE.md#executable-invariants-not-just-reviewed-ones) | Do not repair, normalize or delete committed payload text to enforce a new rule. Derived state remains reconstructible. Equal complete log/time/version inputs must retain equal results. Retaining original text is different from authenticating it. |
| [ADR 0002](../decisions/0002-payload-stored-plaintext-in-v0.md), [0003](../decisions/0003-genesis-sentinels-and-hash-material-delimiters.md), [0007](../decisions/0007-payloads-keyed-by-event-id-not-payload-hash.md) | Canonical plaintext preparation, fixed hash/idempotency material and per-event payload identity remain binding. A different payload commitment is a versioned contract change, not a replacement `_json` helper. |
| [ADR 0014 sections 5-10](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#5-lineage-covers-ancestry-and-result), amended by [0015](../decisions/0015-candidate-scoped-verification.md) | Cover complete logical dependencies, maintain atomic publication and keep old replay/version isolation. Do not silently give an old payload a different decoded meaning. |
| [ADR 0025](../decisions/0025-incremental-result-commitment.md#1-version-and-semantic-scope), [0034 sections 1/10](../decisions/0034-forward-state-transitions.md#1-version-and-dispatch) | Projectors `"0"`, `"1"`, `"2"` retain frozen contracts; projector `"3"` is a separately selected contract, not permission to tighten its shared historical decoder. New-format selection must be explicit; old readers must refuse unsupported formats rather than reinterpret them. |
| [ADR 0030 sections 2-3](../decisions/0030-sole-writer-and-positional-fields.md#2-semantic-and-positional-contents), [0033 sections 2/4](../decisions/0033-projector-0-value-and-verifiability-domain.md#2-value-domain-and-refusal-boundary) | Preserve complete retained semantic text and return original committed pairs on equivalent retries. ADR 0033 demonstrates an explicit admission-only tightening with unchanged historical replay; it does not itself authorize duplicate rejection. |
| [ADR 0011](../decisions/0011-database-schema-versioning.md), amended by [0035 section 1](../decisions/0035-adr-0034-implementation-boundaries.md#1-schema-versions-4-and-5) | Database schema versions and envelope schema versions are distinct. Currently fresh schema is 5 and existing 4 remains supported for `"0"`/`"1"`/`"2"`. No open/read path silently migrates a store. |
| [ADR 0015](../decisions/0015-candidate-scoped-verification.md), [0023](../decisions/0023-stage-two-contract.md), [0024](../decisions/0024-no-authoritative-head.md) | Key/value equality cannot coalesce distinct ClaimCandidates, change support applicability or select a head. Exact property/ID identity and candidate-scoped standing survive any parser change. |
| [ADR 0026](../decisions/0026-usage-is-not-evidence.md) | Parser diagnostics, retrieval exposures and audit frequency are not world evidence, approval or new lineage dependencies. This task supplies no usage log. |

The new-private-codec decisions recorded in
draft [B2, rulings 4-6](0027-b2-private-value-codec-ruling-brief.md#decisions-made)
already specify decoded-key duplicate rejection, no Unicode normalization and
canonical private input. They are design records for Proposed ADR 0027.
They provide no authority to retrofit the plaintext APIs.
Proposed [ADR 0028](../decisions/0028-redaction-and-crypto-shredding.md) supplies no shipped
erasure or migration mechanism for these old stores. Neither proposal is ratified
by this worksheet. Cross-language floats and resource bounds remain separate open
decisions; a duplicate-key rule must not silently settle them.

## 4. Four concrete options for a ruling

Effort is relative engineering scope, not a measured delivery estimate. Each
option requires acceptance before implementation; none changes today's behavior.

### A. Preserve current acceptance; add an explicit inspection diagnostic

- **Contract:** retain last-wins decoding on all shipped paths. An opt-in raw-text
  audit reports duplicate decoded keys, with event ID and object path, without
  rejecting, rewriting or treating the diagnostic as evidence.
- **Replay/determinism:** existing bytes and results stay fixed; the diagnostic is
  outside reduction. Other decoders still need the documented interpretation.
- **Schema/migration:** no schema or hash migration. No persistent diagnostic
  store is needed; adding one would require its own derivative contract.
- **Existing stores:** all currently supported histories remain readable and
  replayable. Existing ambiguous text remains accepted; no stronger commitment
  is claimed.
- **Tests:** pin duplicate/escaped/nested diagnostics, no mutation, unchanged
  append/replay/retry behavior and frozen fixtures. Test diagnostics independently
  of the decoder that discarded the duplicates.
- **Effort:** low. It improves visibility but leaves the permissive input boundary.

### B. Tighten new admission only, with an explicit frozen-admission exception

- **Contract:** refuse duplicate decoded keys on every new ordinary request and
  low-level append, across existing selected projectors. Keep historical decoding
  unchanged. Recognize equivalent committed retries using the old contract before
  applying the new admission check; new conflicting requests still refuse.
- **Replay/determinism:** admitted history replays as before. Admission and replay
  intentionally have different domains, as explicitly established for legacy
  values by ADR 0033. This exception must be ratified rather than inferred.
- **Schema/migration:** no event/table/hash change is necessary; the acceptance
  boundary changes with the software release. An ADR must explicitly amend the
  applicable frozen new-submission promises. A runtime date cutoff is unnecessary.
- **Existing stores:** no rewrite, scan requirement or historical rejection.
  Previously uncommitted duplicate requests now refuse; retained committed
  duplicate requests remain retryable. Old software can still admit them, so this
  does not provide a portable, recorded strictness guarantee for a history.
- **Tests:** both routes, all selected versions, strict policy-file isolation,
  grandfathered retries, conflicting retries, historic rebuild/verifier parity,
  and proof that rejection leaves count, tip and freshness unchanged.
- **Effort:** medium. Retry recognition currently decodes before matching, so
  blindly replacing the shared decoder would violate this option.

### C. Introduce an explicitly versioned duplicate-rejecting payload profile

- **Contract:** a new recorded envelope-schema discriminator selects a plaintext
  payload profile that rejects duplicate decoded keys at every object depth.
  Old envelopes keep their current decoder. New-profile append, reads, replay and
  independent verification apply the same rule. Use an explicitly selected new
  projector contract for new-format histories; do not broaden frozen readers.
- **Replay/determinism:** profile selection is part of retained event data. A new
  reader dispatches by recorded schema, never deployment date/current policy.
  Legacy prefixes use old semantics; mixed-history replay is defined and tested.
  Duplicate-only strictness need not change the canonical-content hash formula.
- **Schema/migration:** `events.schema_version` already exists, but its accepted
  values, parser dispatch, new writer/projector selector and supported-reader
  matrix need an ADR. No new SQL column is inherently required. If no table shape
  changes, do not bump database metadata merely for an envelope value. Any actual
  table change needs separately explicit database compatibility/migration rules.
- **Existing stores:** preserve all old event/payload bytes, IDs and commitments.
  Transition on an explicitly designated working copy, with pre-existing prefix
  equivalence; old readers refuse when they encounter an unsupported new schema.
  Do not relabel historical events as strict or leave two authoritative writers.
- **Tests:** positive old/new/mixed prefixes; new-format duplicate refusal at
  append and replay; frozen refusals; complete replay/publication equivalence;
  old duplicate retries; independent parser vectors. Cover the format boundary
  in the verifier and store-transition proof.
- **Effort:** high relative to B because format dispatch and compatibility become
  explicit public contracts. It gives a durable strictness boundary rather than
  a software-release inference. Numeric cross-language compatibility remains open.

### D. Authenticate exact original payload bytes in a new format

- **Contract:** define a versioned raw UTF-8 commitment, its hash framing and its
  relationship to the existing canonical-content hash/idempotency formula.
  Raw-text authentication does not choose duplicate interpretation; explicitly
  pair it with a decoder rule, preferably duplicate rejection.
- **Replay/determinism:** exact bytes become necessary inputs. A decoder can no
  longer normalize/re-encode before checking the raw commitment. Versioned
  canonical-content interpretation and candidate identity still remain necessary.
- **Schema/migration:** requires a new envelope/commitment contract, discriminant,
  verifier/proof coverage and projector compatibility. Reusing `payload_hash`
  silently with a new meaning is excluded. Any extra columns/storage layout need
  accepted database versioning and explicit migration.
- **Existing stores:** preserve their old commitments and bytes; never pretend
  they had the stronger historical guarantee. Recording a new attestation about
  an old text is not retroactive authentication by the old event.
- **Tests:** altered whitespace/escapes/order must fail the new raw commitment;
  same-value/different-text fixtures, mixed histories, retries and independent
  wire vectors must pass their specified contracts. Compare all old bytes.
- **Effort:** highest. This is appropriate only if exact-text authentication is an
  actual requirement; duplicate refusal alone does not require it.

## 5. Recommendation (not a ruling)

**Recommend C for a durable new strictness contract, with A available as a
separately accepted diagnostic-only interim.** Preserve every shipped history and
its decoder. Reject duplicate decoded keys recursively in the new plaintext
profile, keep exact Unicode identity, and keep the existing canonical-content
commitment. Do not select D unless the maintainer independently requires original
bytes to be authenticated. B is a smaller alternative if the maintainer prefers
an explicit admission-only exception and accepts its weaker recorded guarantee.

For C's narrow plaintext profile, recommend allowing otherwise accepted
noncanonical whitespace/member order: unique keys are the decision here. Do not
describe this as the new private codec or weaken B2's canonical-private-input
ruling. No numeric encoder, integer range, resource bound, protected wire format
or cross-language conformance claim is selected by this recommendation. Their
existing blockers remain. All of this is proposed direction for ratification,
not implementation instructions.

## 6. Exact maintainer questions

Answer column values are proposals only. A different answer changes the ADR
outline before implementation. A choice of A/B/D makes C-specific questions
inapplicable; mark those `N/A`.

| No. | Question | Short answer choices | Recommended answer |
|---|---|---|---|
| 1 | Which option governs this gap? | `A` / `B` / `C` / `D` | `C` |
| 2 | Must every already committed legacy payload keep its existing decoded meaning and bytes? | `Yes` / `No` | `Yes` |
| 3 | Must equivalent committed duplicate-text retries return their original pair? | `Yes` / `No` | `Yes` |
| 4 | For C, is the discriminator the recorded envelope schema, with a new explicit projector selection? | `Yes` / `No` | `Yes` |
| 5 | For new strict input, does duplicate rejection apply at every nested object, including objects inside arrays? | `Yes` / `No` | `Yes` |
| 6 | Compare keys after escape decoding, without case folding or Unicode normalization? | `Exact` / `Normalized` | `Exact` |
| 7 | Reject even repeated keys whose values are equal? | `Yes` / `No` | `Yes` |
| 8 | Must the new plaintext profile also require already canonical input text? | `Yes` / `No` | `No` |
| 9 | Add an original-text commitment in this decision? | `Yes` / `No` | `No` |
| 10 | Keep number serialization/domain and the B2 cross-language/resource questions outside this change? | `Yes` / `No` | `Yes` |
| 11 | Include an optional read-only duplicate diagnostic as an independently scoped interim? | `Yes` / `No` | `Yes` |
| 12 | Use explicit working-copy transition and prefix-equivalence proof for new-format adoption? | `Yes` / `No` | `Yes` |

Questions 2/3 are compatibility requirements of the recommendation. A `No`
requires explicit supersession and its consequences, not an implementer's
fallback. The separate envelope profile name/version and new projector number
must be assigned in the future authority change; `TBD` here reserves neither.

## 7. Acceptance evidence the eventual ADR must require

These are prospective tests, not new tests added by this documentation task.

1. Repeated top-level and nested keys, objects inside arrays, escaped equivalent
   keys and equal-value duplicates refuse under the new strict contract. Keys
   shared by separate objects remain valid. NFC/NFD and case variants stay
   distinct. Include a strict independent pair-preserving parser as an oracle.
2. Unique-key whitespace/order/escape variants retain the agreed acceptance
   behavior and canonical hashes. Duplicate-only hardening must not silently
   change numeric bytes, timestamp spelling or value/candidate identity.
3. Exercise ordinary requests and low-level pairs before append. Failed new
   admission changes no envelope, payload, count, tip, freshness or publication.
   Hash failures remain distinct from duplicate-key refusals.
4. Previously committed duplicate payloads read/replay/rebuild with identical IDs,
   canonical content, lineage, roots and retry pairs under their recorded old
   contracts. Text-only conflicting retries continue to refuse.
5. New strict-format invalid records injected into test fixtures refuse at reads,
   replay, publication and standalone verification; old-format counterparts keep
   their specified behavior. Test mixed cutoffs and unsupported-reader refusal.
6. Compare complete incremental/materialized and genesis-replay results at the
   same time, prefix and projector. Retain projector byte fixtures and independent
   canonical-subset evidence; do not call that subset a full private-codec proof.
7. If C or D is chosen, prove the transition on a disposable working copy before
   new-format appends. Preserve source bytes, IDs and the old-reader boundary.

## 8. Future ADR outline only

**ADR number TBD; Status: Proposed; Implementation: None. No ADR file is created.**

1. **Problem/evidence:** canonical-content commitment versus original text;
   current four-projector/two-route reproductions; no accepted-contract violation
   claimed; scope limited to payload text.
2. **Decision record:** answers 1-12, chosen option, exact decoded-key equality,
   recursive duplicate rule and canonical-input policy; separate legacy,
   plaintext-new-profile and proposed-private-codec boundaries.
3. **Version/authority matrix:** exact new identifiers if C/D; old/new/mixed log
   behavior for append, replay, retry and verifier; required explicit
   supersessions, including any frozen-admission exception if B is chosen.
4. **Commitment/retry contract:** unchanged canonical hashes or explicitly framed
   raw commitment; ciphertext retention; historical committed retry recognition
   before new-admission rules where applicable.
5. **Compatibility/storage:** supported database and envelope schemas kept
   distinct; actual DDL, if needed, decided in the ADR; explicit working-copy
   adoption, refusal and rollback/recovery boundaries; no historical rewrite.
6. **Acceptance and limits:** the matrix above, independent parser evidence,
   frozen bytes, whole-view equality and no candidate/head/evidence side effects;
   unchanged cross-language numeric/resource blockers and public-only policy.
7. **Delivery protocol:** maintainer authority commit first, separately authorized
   implementation and full suite/checker afterward, then the separate maintainer
   implementation marker. This worksheet is not any of those commits.
