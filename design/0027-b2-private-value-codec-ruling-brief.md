# ADR 0027 B2: private-value codec ruling brief

**Status:** Non-authoritative ruling brief recording the maintainer's six MADE
rulings in [Rulings](#rulings). Remaining choices are explicitly open. No schema
draft, codec implementation, ADR ratification or Gate 1 pass is supplied here.

**Baseline:** `63f75c92fa5deb13f0dd4ed8e334d307365d96fc`, Python 3.14.2,
2026-09-14. Scope is B2 in the
[Gate 1 worksheet](0027-gate1-worksheet.md#b2-cross-language-private-value-codec).
The observations below concern existing code and synthetic inputs, not production
data, a cross-language implementation or a cryptographic conformance result.

## The recorded gap

[ADR 0027, Remaining unresolved questions](../decisions/0027-stage-three-authority-and-acceptance.md#remaining-unresolved-questions):

> **Private value codec:** What exact cross-language value/number domain and
> decoding rules does `nyx-private-json/1` admit, and which fixtures establish
> compatibility with existing values without changing frozen canonical bytes?
> Signing a fixed opaque byte string is settled; producing and semantically
> interpreting that string from independent value models is not.

An implementer can retain and authenticate a given P without knowing how every
admitted private value is represented and decoded by another language. B2 closes
that missing semantic contract. None of the observed Python behaviors below
automatically supplies the missing cross-language decision.

## Constraints already stated

[ADR 0027 §3.1](../decisions/0027-stage-three-authority-and-acceptance.md#31-public-wire-profile-and-commitment-calculation):

> P is the exact UTF-8 private JSON byte string prepared once by the writer, with
> codec `nyx-private-json/1`. In-tree preparation uses the existing canonical JSON
> serializer, preserving integer/float distinctions and accepted value spellings;
> the crypto layer never decodes/re-encodes P. Cross-language private-number/value
> decoding and its conformance vectors remain an explicit ratification blocker,
> not permission to round numbers or silently substitute RFC 8785 for Python's
> serialization.

That section also already specifies:

- A separate public profile, with integer-only public numbers, scalar-value key
  ordering, strict public parsing and canonical persisted/signed public objects.
  Private claim values are expressly excluded from its numeric restrictions.
- Authentication of G/AAD and the AEAD tag before decoding private content.
- Fixed P, key, nonce and public inputs must yield identical wire objects across
  implementations. Independently encrypted equal values need not yield equal
  ciphertext. Retries retain the exact sealed body.
- Existing hashes and frozen fixtures must not be retrofitted with new framing
  or stricter old-version parsing.

These are constraints within the Proposed contract, not open alternatives in this
brief. The exact UTF-8 requirement supplies no permission to accept invalid UTF-8.
The escaped-string and private-parser observations below concern valid UTF-8
input. Their current decision status is recorded in Rulings and the question lists.

| Existing authority | Constraint on a B2 ruling |
|---|---|
| [ADR 0014 §6](../decisions/0014-cross-belief-reducer-and-hash-lineage.md#6-canonical-serialization) | Shared canonical JSON: sorted object keys, compact separators, preserved Unicode and UTF-8 hashing; no normalization of recorded timestamps or values. Semantic sets use canonical UTF-8 ordering, while semantic sequences retain order. |
| [ADR 0025 §§1–6](../decisions/0025-incremental-result-commitment.md#decision) | Frozen versions remain unchanged. Commitments cover complete candidate/dependency content; map and lineage representations cannot drop value distinctions or members. |
| [ADR 0015 §§1/3/4](../decisions/0015-candidate-scoped-verification.md#decision), [ADR 0024 §§1–3](../decisions/0024-no-authoritative-head.md#decision) | Candidate identity and verification do not derive from value equality. Codec equality cannot coalesce candidates, select an authoritative head or supply corroboration. |
| [ADR 0022 §§1–2](../decisions/0022-belief-container-uniqueness.md#decision), [ADR 0023 §§1/2/4](../decisions/0023-stage-two-contract.md#decision) | Preserve current subject/property association, exact opaque property identity, fresh ordinary candidates and retained retries. No identifier normalization or implicit redirection. |
| [Implementation companion §1](../spec/NYX_V0_IMPLEMENTATION.md#1-deterministic-algorithms-no-tuning--implement-exactly), subject to those ADRs | The shipped serializer uses Python JSON float representations. No separate fixed-float format is implemented. |

## Existing implementation and evidence limits

[hashing.py](../src/nyx/hashing.py), `canonical_json`, calls
`json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
It does not supply a custom number encoder or disable nonfinite-number output.
`canonical_set` deduplicates and sorts by encoded bytes, rather than Python value
equality. `_sha256_hex` encodes its string argument as UTF-8.

[events.py](../src/nyx/events.py), `build_event`, prepares canonical plaintext
payload text and its legacy commitments. [integrity.py](../src/nyx/integrity.py),
`_json`, calls the default `json.loads`; `decode_payload` then validates the
decoded object and its recomputed canonical commitments. These functions are
existing unencrypted paths, not an implementation of `nyx-private-json/1`.
Consequently parser acceptance alone does not establish that arbitrary input
text passes full event integrity validation.

The probe used these functions directly, entirely in memory. Encoder rows below
apply `canonical_json(value)`, UTF-8 encoding and `json.loads`. Decoder rows apply
`integrity._json(text, "synthetic")` and re-serialize the result. Displayed backslash
escapes identify the input characters; they are not a proposal for new wire bytes.

| Synthetic input | Observed result on the recorded runtime | Boundary exposed |
|---|---|---|
| Python `1`, `1.0`, `-0.0` | Encoded as `1`, `1.0`, `-0.0`; decoded types are int, float, float | Integral floats and signed floating zero retain distinct spellings. |
| `2**53 + 1` versus `float(2**53 + 1)` | `9007199254740993` versus `9007199254740992.0` | Conversion before serialization can already have lost precision; preserving P cannot undo it. |
| Python `10**99` | Exact 100-digit integer survives encoding/decoding | Existing examples exceed a binary64-only integer model. This does not establish an unlimited protocol range. |
| Python `1e-7`, `1e20` | `1e-07`, `1e+20` | Existing exponent spellings must be accounted for; the public integer profile cannot supply this rule. |
| Smallest positive binary64 subnormal; largest finite binary64 value | `5e-324`; `1.7976931348623157e+308` | Finite range endpoints and subnormal decoding need cross-language coverage. |
| Python nonfinite floats | `NaN`, `Infinity`, `-Infinity`, decoded back to floats | The existing helper emits/accepts these tokens. Ruling 1 excludes them from the new codec only. |
| JSON text `1e0`, `-0` | Re-encoded as `1.0`, `0` | Default decoding loses original numeric token spelling. |
| JSON text `1e400`, `1e-400` | Re-encoded as `Infinity`, `0.0` | Default parsing can overflow or underflow; successful parsing is not exact interpretation. |
| JSON text `0.100000000000000005` | Re-encoded as `0.1` | Default parsing can round before any re-encoding occurs. |
| JSON text `{"x":1,"x":2}` | Re-encoded as `{"x":2}` | Earlier duplicate members disappear. |
| JSON text `{"1":"a","\u0031":"b"}` | Re-encoded as `{"1":"b"}` | Different key spellings can decode to the same key. |
| JSON text with surrounding spaces, `  {"x":1}  ` | Accepted, re-encoded without spaces | Current parser permissiveness does not define allowed private wire spellings. |
| JSON string token `"\ud800"` | Decoder returns a lone surrogate; UTF-8 encoding of the serializer's resulting string raises `UnicodeEncodeError` | Valid ASCII escape syntax can produce a value outside the UTF-8 output path. |
| Python strings U+00E9 and U+0065 U+0301 | Distinct canonical strings | The serializer does not normalize Unicode. |
| Python tuple `(1, 2)`; dictionary `{1: "x"}` | Decode as list `[1,2]`; object with string key `{"1":"x"}` | Host-language convenience conversions do not preserve all input types. |
| Python `Decimal("0.1")` | `TypeError` from the existing encoder | A host-language numeric type does not imply codec support. |
| JSON text `01`, `+1`, `[1,]` | `IntegrityError` from `_json` | The current decoder has rejection boundaries as well as permissive cases. |

The runtime reported `sys.get_int_max_str_digits() == 4300`. That is an observed
interpreter setting, not a Nyx wire limit. No boundary-size or resource-exhaustion
experiment was performed. Nesting, collection-size and string-size limits were
not exhaustively characterized.

The set helper returned `[-0.0,0,1,1.0,true]` for the synthetic members
`[1, 1.0, True, 0, -0.0]`. This documents byte-based set handling; it establishes
no new semantic equality rule for claim values or candidate identity.

### Replay scope of the numeric observation

For each of 13 numeric inputs (the ten finite examples represented above and
the three nonfinite values), the probe constructed a fresh two-event synthetic
log: one constitutive mention and one observation with a single fresh candidate.
Both used observed origin, direct-observation source class, explicit IDs and
`2026-09-14T00:00:00Z` for recorded/occurred time. The observation referenced the
mention's event hash and recorded mention/subject IDs. Its claim supplied an
explicit property, belief ID and `externally_checkable` verifiability.

Each pair passed `integrity.decode_payload`; `projection.project_snapshot` under
both `"1"` and `"2"` returned the same serialized candidate value as the encoder
row. This includes `NaN`, `Infinity` and `-Infinity`. No SQLite store was created,
and this probe did not test storage append, projector 0, every downstream consumer
or semantic comparison of nonfinite values. It neither declares those values safe
nor requires a future codec to admit them. It establishes a compatibility case
that must be addressed explicitly rather than assumed absent.

### What existing tests establish

- [test_reducer_boundary.py](../tests/test_reducer_boundary.py),
  `test_version_zero_golden_bytes_and_no_retrofit`, checks the retained
  [version-0 fixture](../tests/fixtures/version0_ordinary.json).
  `test_canonical_sets_preserve_unicode_and_ordered_path_edges` covers set and
  path ordering.
- [test_incremental_commitment.py](../tests/test_incremental_commitment.py),
  `test_version_one_probe_bytes_remain_frozen`, pins the 32-observation lineage
  probe to 914,109 bytes and digest
  `aac6b0e626261a46069debe46cf450a755ebec601535fab3e1731ec6742f7c6f`.
  The suite also checks replay, roots and version isolation on its fixtures.
- [check_docs.py](../scripts/check_docs.py), `check_serialization`, checks four
  serialization samples plus one set sample. Samples include scalar-order Unicode
  keys, string escapes and `1` versus `1.0`. It explicitly reports that finite
  samples do not prove Proposed wire/parser/crypto conformance or all number formats.

These existing fixtures constrain changes to old behavior. They are not a complete
value-domain specification, a cross-language vector corpus, or a Gate 1 pass.

## Rulings

**Recorded 2026-09-14: maintainer decisions MADE.** These rulings apply to the
**new codec only**. Frozen projectors **"0", "1" and "2" retain their existing
contracts unchanged**, including parsing, serialization and committed bytes.
The `allow_nan=False` requirement below does not authorize changing the shared
legacy helper in `src/nyx/hashing.py`. Recording rulings in `design/` does not
ratify the Proposed ADR or authorize implementation.

### Decisions MADE

1. **Nonfinite values — MADE.** NaN, Infinity and -Infinity are not admitted.
   Encoding must set `allow_nan=False`; decoding must reject the bare `NaN`,
   `Infinity` and `-Infinity` tokens.
2. **Exact integers — MADE.** Exact integers are preserved exactly. This settles
   preservation, not the still-open admitted integer range.
3. **Finite binary64 values — MADE.** Finite floats preserve binary64
   distinctions: the codec reproduces the recorded binary64 value. It does
   **NOT** preserve an arbitrary decimal exactly and must never silently convert
   an exact decimal or a large integer into a binary64 approximation.
   Exact-decimal support, if ever wanted, requires its own separate contract and
   is out of scope here. Preservation includes the binary64 signed-zero
   distinction; its exact wire spelling remains open below.
4. **Duplicate object keys — MADE.** Reject duplicate keys, compared after
   escape decoding: `"x"` and `"\u0078"` collide and are rejected. Equality is
   exact byte/codepoint-level equality after escape decoding (the same decoded
   codepoint sequence, equivalently its UTF-8 bytes), not equality of raw escape
   spellings. It does **not** include Unicode canonical equivalence. Composed and
   decomposed forms remain distinct keys, following ruling 5.
5. **Unicode — MADE.** Reject lone surrogates. Preserve Unicode without
   normalization.
6. **Canonical private input — MADE.** Private wire input must already be
   canonical. The decoder validates canonicality and never replaces the retained
   authenticated bytes. Conversion from human-facing input is a separate upstream
   step outside this codec. Canonicality validation does not waive the existing
   authentication-before-decoding boundary.

### Still open before B2 passes Gate 1

- **O1: Complete float encoding specification — OPEN; maintainer ruling.** An
  independent implementer still needs digit selection, exponent thresholds,
  exponent spelling and negative-zero rules. Python's `repr` implements a
  published shortest-round-trip algorithm which could be cited rather than
  re-derived; no algorithm citation is selected by this record. Exponent spelling
  and negative zero still require explicit rules either way. **"Use Python's
  serializer" is not an acceptable specification.** The maintainer selects the
  normative rules/reference; the independent reviewer assesses their completeness,
  interpretation and commitment/parser consequences against the frozen evidence.
  The later [Float encoding specification](#float-encoding-specification) now
  supplies executable mathematical/formatting rules and generated vectors for
  reproducing the current finite-float bytes. This is specification evidence,
  not an additional MADE ruling or approval of the complete new codec; the
  remaining confirmation/review questions are listed there.
- **O2: Numeric and resource bounds — OPEN; maintainer ruling.** Integer range,
  string length, nesting depth and total document size remain unset. Exact integer
  preservation does not choose an unlimited range or an interpreter's incidental
  limit. The maintainer chooses the bounds and required out-of-bound behavior;
  the independent reviewer assesses their protocol implications and evidence.
- **O3: Explicit JCS alternative — OPEN; maintainer ruling.** Whether adopting
  JCS under a new projector version remains available as an explicit, non-silent
  alternative if the full encoding specification dominates the cost is undecided.
  ADR 0027 §3.1 rules out silent substitution, not explicit adoption. This records
  an open alternative, not JCS adoption or a change to rulings 1–6. Any eventual
  choice must explicitly account for those rulings and the version boundary;
  the independent reviewer assesses the resulting specified contract.

Questions 1–11 below retain any additional unresolved specification and evidence
scope; none is silently closed by these six rulings. Complete canonical rules and
positive/negative interoperability vectors remain required by Gate 1. The
maintainer determines application requirements and the candidate evidence scope.
Gate 2's independent cryptographer supplies independent judgment of the pinned
protocol and evidence, not the maintainer's application rulings. Reviewer scope,
findings and remediation remain outstanding; this record does not move Gate 2
ahead of Gate 1 or claim either gate passed. Gate 3 implementation/operational
assurance also remains separate. No B2-specific storage/recovery ruling is made.

## Questions requiring maintainer rulings

The status labels below supersede the earlier statement that every question was
unanswered. A question marked **Still open** identifies both its resolved portions
and its remaining scope. Per-event field shapes and nullability remain B1 work.

1. **Admitted value and integer domain — Still open.** Rulings 1–3 settle
   nonfinite exclusion and integer/binary64 preservation; ruling 5 settles the
   Unicode restriction. The complete recursive domain and integer range remain
   open (O2). What exact recursive private value
   domain is admitted, and what integer range must every implementation preserve?
   What distinguishes integers, floating values and booleans in the decoded
   model? Integer/float preservation is already required; the complete domain
   and representability requirements are not supplied by Python's host types.
2. **Finite-number interpretation and production — Still open.** Ruling 3
   settles binary64 preservation and forbids silent decimal/integer approximation.
   Exact wire production and capacity behavior remain open (O1/O2).
   What exact decoding and
   writer rules preserve admitted finite values across languages, including
   signed zero, integral floats, precision boundaries, subnormals and exponent
   spellings? How is a consumer unable to represent an admitted value required
   to behave? No rounding permission can be inferred from the shipped decoder.
3. **Nonfinite values and compatibility — Resolved by ruling 1 and the Rulings
   version boundary.** Nonfinite values are excluded from the new codec; frozen
   projectors retain their contracts. No migration is authorized. Compatibility
   evidence coverage remains in questions 7/10/11, not a reopened admission choice.
4. **Private token grammar and object decoding — Still open.** Rulings 4–6
   resolve duplicate-key rejection, Unicode handling, canonical-input-only
   acceptance and preservation of authenticated P. The complete canonical byte
   grammar, including O1's numeric spellings, still needs specification.
   Which private byte strings are
   admissible beyond the fixed UTF-8 requirement and stated in-tree writer?
   Which exact canonical spellings govern escapes and number tokens? The decoder
   must reject noncanonical input under ruling 6, rather than repair it.
5. **String domain — Resolved by ruling 5.** Lone surrogates are rejected and
   Unicode is preserved without normalization; invalid UTF-8 is already excluded.
   String bounds remain in O2/question 6 and exact wire spellings in question 4.
6. **Host adaptation and interoperable limits — Still open.** Ruling 6 places
   human-facing conversion upstream and outside the codec; ruling 3 prohibits
   silent numeric approximation. Exact host API/type boundaries and interoperable
   bounds/capacity behavior remain open (O2); no tuple/key-conversion default is
   supplied. What host inputs are admitted
   before writer preparation, including convenience conversions of tuple/list
   and non-string object keys? Which number-size, nesting or other bounds belong
   to the interoperable codec rather than incidental interpreter settings?
   What observable result is required when a value exceeds a permitted bound or
   a consumer's capacity? This does not choose fields or error codes for B1.
7. **Compatibility and conformance coverage — Still open.** Rulings 1–6
   constrain required outcomes; they do not supply the B5 vector corpus or its
   reviewed coverage. This needs maintainer-defined scope and independent review.
   Which exact existing-value cases
   and cross-language outcomes must the frozen B5 evidence establish for these
   rulings? What demonstrates preservation of both encoded bytes and decoded
   type/value, rather than two implementations merely accepting the same input?
   Which private-input cases must reject? Producing verified expected outputs
   remains evidence work after the relevant semantics are settled.

The input-domain rulings constrain writer/decoder behavior; those together
constrain the vector results. This is a dependency statement, not a proposed
codec or implementation sequence. Answers are limited to the explicit rulings.

## Dependencies and handoff boundary

B2 supplies value/decoding definitions needed by B1's protected-content schemas
and B5's cross-language evidence. B3's compound-custody representation remains
independent. [ADR 0028 §3](../decisions/0028-redaction-and-crypto-shredding.md#3-key-binding-and-custody)
inherits the same codec and authentication-before-decoding contract; it supplies
no alternative default. Erased plaintext cannot be semantically decoded merely
because its original signature survives.

There is no prior 0020 authority ruling required for this work.
[ADR 0027 §§2/9](../decisions/0027-stage-three-authority-and-acceptance.md#9-exact-supersessions-and-limits)
already state the limited proposed authority scope. Contributor write/read
permissions and the other excluded policies remain open. Historical authorization
at the pre-event prefix remains a constraint on relevant records, regardless of
the eventual codec.

The maintainer rules on the application value domain and required behavior.
Gate 2's independent cryptographer reviews the completed protocol's parser,
byte-commitment and authenticated-decoding boundaries, including resulting
conformance evidence; that review does not select the application's values.
Gate 1 evidence and explicit ratification remain necessary before implementation.
This brief records partial B2 closure through the six rulings; B2 remains
Gate 1-incomplete and this brief supplies no cryptographic assurance.

## Findings: cross-language verifiability of canonicalization

**Evidence date/runtime:** 2026-09-14; the same source commit identified above;
CPython 3.14.2 and Node.js v24.11.1. All probes were throwaway inline checks.
Synthetic appends used SQLite `:memory:` with the repository schema. Existing
seed stores were opened with `mode=ro`, `query_only=ON` and a read transaction.
This findings section supplied no production implementation, source change, new
test file or ruling; the later maintainer decisions are recorded separately above.
File:line locators below refer to that source revision.

### 1. Encoder behavior and the JSON boundary

[src/nyx/hashing.py:30](../src/nyx/hashing.py) passes `sort_keys=True`,
`separators=(",", ":")` and `ensure_ascii=False`; it does **not** pass
`allow_nan=False`. Inline calls confirmed these exact unquoted outputs:

| Call | Output text |
|---|---|
| `canonical_json(float('nan'))` | `NaN` |
| `canonical_json(float('inf'))` | `Infinity` |

**These bare tokens are not valid JSON under RFC 8259 §6.** Strict JSON decoders
in other languages reject them: Node's `JSON.parse` raised `SyntaxError` for
`NaN`, `Infinity` and `-Infinity`. RFC 8259 §9 permits parsers to accept extensions,
so this is not a claim that every conformant parser must reject every extension.
It is a failure of portable JSON grammar, and §10 requires generators' JSON text
to conform to that grammar. [RFC 8259 §§6/9/10](https://www.rfc-editor.org/rfc/rfc8259).

Python explicitly documents its default nonfinite extension and last-wins
duplicate-name decoding. Neither behavior is an independently specified Nyx
private codec. [Python JSON compliance notes](https://docs.python.org/3.14/library/json.html#standard-compliance-and-interoperability).

### 2. Complete call-site inventory and external-payload reachability

An AST enumeration of every `src/nyx/*.py` file and `scripts/verify_store.py`
found **42 calls to `canonical_json`** and **31 calls to `json.loads`**. Each
decode call has one positional input and no keyword arguments. Thus none passes
`object_pairs_hook`, `parse_float`, `parse_int` or `parse_constant`, including
the independently organized verifier. Two calls on the same line are counted
separately. Definitions and docstring examples are not counted as call sites.

The canonicalization call sites and their uses are:

| File:line sites | Inputs/purpose |
|---|---|
| [src/nyx/hashing.py:39,74,85,95](../src/nyx/hashing.py) | Set identity/order; idempotency; envelope hash; dependency hash. |
| [src/nyx/events.py:112,113,114,145](../src/nyx/events.py) | Source, entity references, payload commitment input and stored payload text. |
| [src/nyx/integrity.py:90](../src/nyx/integrity.py) | Recompute payload commitment from decoded content. |
| [src/nyx/reducer.py:37,80,192,261,292](../src/nyx/reducer.py) | Snapshot storage/update; detached dependency payload and claim; version-1 lineage. |
| [src/nyx/committed.py:21,30,35,196,264,305](../src/nyx/committed.py) | Pair and identity keys; result root; detached payload and claim; version-2 lineage. |
| [src/nyx/committed_storage.py:62,64,83](../src/nyx/committed_storage.py) | Publication material, root descriptors and stored belief headers. |
| [src/nyx/merkle.py:13,58,70,78,125,219,229,234](../src/nyx/merkle.py) | Empty digest, routing, node/leaf creation, equality, proof reconstruction, canonical stored-node validation and decoded leaf retention. |
| [src/nyx/storage.py:740,754,760](../src/nyx/storage.py) | Serialized belief, link and other projected records. |
| [src/nyx/skeleton.py:82](../src/nyx/skeleton.py) | Retained-submission source comparison. |
| [scripts/verify_store.py:45,135,253 twice,352,414,508](../scripts/verify_store.py) | Digest helper, canonical node check, expected/stored comparison, identity keys, member keys and current-pair index reconstruction. |

The full decode inventory follows. **No** means that argument is absent, rather
than an explicit custom implementation of the corresponding behavior.

| Call site | Decoded input | object_pairs_hook | parse_float | parse_int | parse_constant |
|---|---|---|---|---|---|
| [src/nyx/integrity.py:41](../src/nyx/integrity.py) | `_json`: source, references or payload text | No | No | No | No |
| [src/nyx/integrity.py:92](../src/nyx/integrity.py) | Envelope source for idempotency validation | No | No | No | No |
| [src/nyx/storage.py:487](../src/nyx/storage.py), first call | Legacy supporting-event list | No | No | No | No |
| [src/nyx/storage.py:487](../src/nyx/storage.py), second call | Legacy opposing-event list | No | No | No | No |
| [src/nyx/storage.py:488](../src/nyx/storage.py) | Legacy superseding-event list | No | No | No | No |
| [src/nyx/storage.py:570](../src/nyx/storage.py) | Materialized snapshot records | No | No | No | No |
| [src/nyx/storage.py:606](../src/nyx/storage.py) | Named projected record | No | No | No | No |
| [src/nyx/storage.py:905](../src/nyx/storage.py) | Belief/status content | No | No | No | No |
| [src/nyx/committed.py:91](../src/nyx/committed.py) | Committed belief leaf/header | No | No | No | No |
| [src/nyx/committed.py:190](../src/nyx/committed.py) | Envelope source | No | No | No | No |
| [src/nyx/committed.py:196](../src/nyx/committed.py) | Canonical payload copy | No | No | No | No |
| [src/nyx/committed.py:264](../src/nyx/committed.py) | Canonical claim copy | No | No | No | No |
| [src/nyx/committed_storage.py:45](../src/nyx/committed_storage.py) | Loaded leaf value/header | No | No | No | No |
| [src/nyx/merkle.py:79](../src/nyx/merkle.py) | Canonical leaf value during construction | No | No | No | No |
| [src/nyx/merkle.py:116](../src/nyx/merkle.py) | Named leaf value | No | No | No | No |
| [src/nyx/merkle.py:167](../src/nyx/merkle.py) | Enumerated leaf value | No | No | No | No |
| [src/nyx/merkle.py:191](../src/nyx/merkle.py) | Node body while generating a proof | No | No | No | No |
| [src/nyx/merkle.py:228](../src/nyx/merkle.py) | Stored node body before canonical/hash validation | No | No | No | No |
| [src/nyx/reducer.py:44](../src/nyx/reducer.py) | Named snapshot record | No | No | No | No |
| [src/nyx/reducer.py:47](../src/nyx/reducer.py) | Enumerated snapshot records | No | No | No | No |
| [src/nyx/reducer.py:128](../src/nyx/reducer.py) | Envelope entity references | No | No | No | No |
| [src/nyx/reducer.py:186](../src/nyx/reducer.py) | Envelope source | No | No | No | No |
| [src/nyx/reducer.py:192](../src/nyx/reducer.py) | Canonical payload copy | No | No | No | No |
| [src/nyx/reducer.py:261](../src/nyx/reducer.py) | Canonical claim copy | No | No | No | No |
| [src/nyx/skeleton.py:131](../src/nyx/skeleton.py) | Submitted stage-two payload for result lookup | No | No | No | No |
| [scripts/verify_store.py:112](../scripts/verify_store.py) | Stored Layer A payload | No | No | No | No |
| [scripts/verify_store.py:133](../scripts/verify_store.py) | Stored committed node | No | No | No | No |
| [scripts/verify_store.py:211](../scripts/verify_store.py) | Legacy evidence lists | No | No | No | No |
| [scripts/verify_store.py:219](../scripts/verify_store.py) | Version-1 projected records | No | No | No | No |
| [scripts/verify_store.py:238](../scripts/verify_store.py) | Version-2 cached headers | No | No | No | No |
| [scripts/verify_store.py:327](../scripts/verify_store.py) | Envelope source during reconstruction | No | No | No | No |

[src/nyx/cli.py](../src/nyx/cli.py) contains **no** `json.loads` or
`canonical_json` call. It consumes storage results and uses `json.dumps` for
presentation at lines 129, 140 and 160. The scan also covers `events.py`,
`skeleton.py` and the remaining source modules, rather than assuming the files
named in the task exhaust the call sites.

#### Duplicate keys are reachable through the public append API

Inline decoding of the distinct UTF-8 texts `{"value":1,"value":2}` and
`{"value":2}` produced the same object, `{'value': 2}`. Canonicalizing that
object gave the same commitment in both cases:
`49c987621f206f09e5fbe23b516b55a36f838cb14867961f1d84a554d3a35b6b`.
This is decoding information loss, not a SHA-256 collision.

Ordinary `build_event` preparation emits Nyx-encoded payload text, but **not all
admissible Layer A payload text must originate in that encoder**:

- [src/nyx/storage.py:289](../src/nyx/storage.py) accepts an `Envelope` and
  `Payload` from its caller. Lines 310 and 397 call `integrity.decode_payload`;
  lines 327–330 and 413–415 insert the supplied `payload.ciphertext` itself.
- [src/nyx/integrity.py:90,93,105,106](../src/nyx/integrity.py) validates hashes
  from the decoded object's canonical form. It does not require that original
  payload text equal that form. Its argument is already text, so the demonstrated
  external-byte route is caller-authored UTF-8 text supplied as `Payload.ciphertext`,
  not an additional undocumented binary-import endpoint.
- [src/nyx/ingestion.py:56](../src/nyx/ingestion.py), `submit`, forwards a retained
  pair into the append path. The typed pair is not proof that its text was emitted
  by `build_event`. The CLI itself is read-only and supplies no import command.

For each projector `"0"`, `"1"` and `"2"`, a synthetic observation was built with
`value: 2` and valid commitments. Before its first append, its payload text was
replaced with text containing `"value":1,"value":2`; envelope and payload hashes
were left intact. For stages 1/2, a valid mention was appended and materialized
first. All three observation appends returned `True`. SQL readback retained the
duplicate-key text exactly; `read_all_events` exposed only value 2. Running
`scripts.verify_store.read_log` on each synthetic store reported zero failures.
These probes exercised the ordinary API, not direct insertion into Layer A tables.

An exact retry is a different boundary: [src/nyx/storage.py:375–382](../src/nyx/storage.py)
compares the retained pair and refuses different text on a retry. Also,
[src/nyx/merkle.py:228–230](../src/nyx/merkle.py) and
[scripts/verify_store.py:133–135](../scripts/verify_store.py) require stored node
text to equal its canonical re-encoding. The Layer A result must not be generalized
to claim that duplicate-key Merkle node bodies pass those checks.

### 3. Float bytes, hashes and the limit of verifier independence

For finite floats, the current helper emits Python's shortest-round-trip `repr`
formatting, including Python's exponent conventions and signed-zero spelling.
The CPython 3.14.2 Python encoder calls `float.__repr__`; its C encoder calls
`PyFloat_Type.tp_repr`. [Python encoder source](https://github.com/python/cpython/blob/v3.14.2/Lib/json/encoder.py#L224),
[C encoder source](https://github.com/python/cpython/blob/v3.14.2/Modules/_json.c#L1327),
[Python floating-point explanation](https://docs.python.org/3.14/tutorial/floatingpoint.html).
Shortest round trip does not imply that every language chooses identical
fixed/exponential notation or preserves the same zero spelling.

The inline comparison used `hashing.canonical_json(v)` and Node's default
`JSON.stringify(v)`, hashing the resulting UTF-8 number text without a newline
or surrounding JSON-string quotes. No object-key sorting difference is involved.

| Case/value | Python text | Node text | SHA-256 comparison |
|---|---|---|---|
| Exponent boundary, `1e-6` | `1e-06` | `0.000001` | Different |
| 17-significant-digit value, `1.2345678901234567e20` | `1.2345678901234567e+20` | `123456789012345670000` | Different |
| Negative zero | `-0.0` | `0` | Different |
| 17-digit control, `1.0000000000000002` | `1.0000000000000002` | `1.0000000000000002` | Equal |

Full observed digests, in the same order:

| Case | Python SHA-256 | Node SHA-256 |
|---|---|---|
| Exponent boundary | `1187132475a4431d8ce6b306fecd75b877993db3279c7769716dacb5ed57e6b7` | `159fb29a827ad04b260aa6c8ab6d8637f8f2b38af5c4f3cb49d6a21205e040f8` |
| 17-digit exponent/fixed | `ecc1c75212d1c6e26af67645b76620c10e9afe9abf35598908529f4b926776bb` | `7905ecd736dd3189ff230dbf333307c03dcfd614e3f2b198752696d618449262` |
| Negative zero | `c26617c7ccbcaa6631b45d851b8cf56e21d2ca624bdb1193afdbd4b560702cec` | `5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9` |
| 17-digit control | `19119a03721db7fc2a2f06afad179bdd384cc44b54e1d4f4f57e374c5b44fbd0` | `19119a03721db7fc2a2f06afad179bdd384cc44b54e1d4f4f57e374c5b44fbd0` |

The disagreement occurs before hashing. Neither the name JSON nor matching
decoded numeric values establishes matching commitment bytes. The control also
shows that 17 significant digits alone do not imply disagreement.

[scripts/verify_store.py:2–7](../scripts/verify_store.py) already discloses shared
hashing/Merkle primitives. Its digest at line 45 uses the same `canonical_json`;
its payload parser at line 112 uses the same Python default behavior. Lines
185–198 rebuild roots through the shared Merkle implementation. It independently
reconstructs records relative to the production readers/reducers, but does **not**
independently implement or cross-check the parser and canonicalization contract.
Thus its passing result cannot expose a shared last-wins interpretation or prove
that a foreign-language verifier will reproduce these bytes. The synthetic
duplicate-key result demonstrates that limit directly.

[ADR 0014:129–188](../decisions/0014-cross-belief-reducer-and-hash-lineage.md)
requires lineage to cover complete result/ancestry and specifies shared canonical
serialization. [ADR 0025 §§2–6](../decisions/0025-incremental-result-commitment.md)
preserves that content coverage while moving it into nodes/roots. Changing a
number's encoding can therefore affect payload commitments, nodes, roots and
lineage wherever that content is covered, not merely a displayed value.

For proposed [ADR 0027:845–862](../decisions/0027-stage-three-authority-and-acceptance.md),
Gate 2 requires independent protocol judgment against a pinned candidate; the
shared Python verifier is not that judgment or proof of a closed foreign-language
codec. [ADR 0027:864–900](../decisions/0027-stage-three-authority-and-acceptance.md)
Gate 3 explicitly includes frozen-vector conformance, independent code review,
canonical serialization and parser strictness. Reusing the same serializer in
writer and verifier cannot by itself establish that part of assurance. These
limits do not reopen the already specified public wire profile or select a new
private representation.

### 4. Floats in the available seeds and fixtures

The inspected persisted corpus is exactly the two existing seed databases under
`scratch/` and `tests/fixtures/version0_ordinary.json`. No claim is made about
unavailable stores, deleted history or every database ever created by a test.

The read-only scan visited every table row and checked direct SQL floating values
plus the stored JSON columns `ciphertext`, `source`, `entity_refs`, `content`,
`supporting_events`, `opposing_events` and `superseding_events`. Decoded arrays and
objects were traversed recursively. Source/reference JSON inside event envelopes
was covered by its Layer A columns. No secret or production corpus was inspected.

| Existing artifact | Evidence inspected | Observed floats |
|---|---|---|
| `scratch/demo-p0.sqlite` | 9 events; 32 total table rows; 36 non-null JSON cells | 0 in decoded JSON; 0 direct SQL float cells |
| `scratch/demo-p2.sqlite` | 11 events; 174 total table rows; 156 non-null JSON cells, including retained committed nodes | 0 in decoded JSON; 0 direct SQL float cells |
| [tests/fixtures/version0_ordinary.json](../tests/fixtures/version0_ordinary.json) | Entire JSON object, plus 6 embedded source/expected-canonical JSON strings | 0 at either level |

During an in-memory replay of the seed logs, a temporary wrapper counted actual
`canonical_json` inputs: **54 calls / 0 float occurrences** for projector 0 and
**691 calls / 0 float occurrences** for projector 2, at the synthetic cutoff
`2026-09-14T00:00:00Z`. The wrapper was restored immediately. The seed generator
uses string observation values at [scripts/seed_store.py:115–130](../scripts/seed_store.py),
consistent with these measurements. The inspected JSON corpus has only strings,
integers, booleans and nulls as scalar leaves.

**No float was committed in the inspected seed logs or retained JSON event
fixture.** However, the broader existing test fixtures do exercise floats:

- [tests/test_reducer_boundary.py:297–305](../tests/test_reducer_boundary.py)
  constructs arbitrary snapshot records containing `1.25` under every record
  kind. Reproducing that constructor sent the value through
  [src/nyx/reducer.py:37](../src/nyx/reducer.py); reading the snapshot returned six
  float occurrences. This is supplied snapshot state, not an accepted Layer A log.
- [tests/test_reducer_boundary.py:196–210](../tests/test_reducer_boundary.py)
  supplies `1.0` in unauthorized confidence fields. Event preparation serializes
  those invalid fixtures before the tests assert append/replay refusal.
- [scripts/check_docs.py:455–468](../scripts/check_docs.py) exercises `1.0` in its
  compatibility samples. This is helper coverage, not committed observation data.

Therefore the statement that all current fixtures are float-free is false.
Excluding floats would leave the **inspected persisted corpus's values** unaffected,
but would narrow the existing encoder/replay value domain and affect float-bearing
helper fixtures. It cannot be called a universal no-op or justified by a claim
that no float has ever been committed anywhere. The earlier synthetic numeric
replay observations remain separate from this persisted-corpus inventory.

### 5. Python-version stability

**Cross-Python-version stability is unverified by this work**, for floats and for
the string/integer/boolean/null and collection classes inspected here. Only the
recorded CPython 3.14.2 runtime was executed; Node supplies a language comparison,
not a Python-version matrix. Sorted keys and compact separators specify important
parts of serialization but are not an empirical guarantee across interpreters.

The official Python account describes the transition to shortest float display
starting with Python 3.1. It does not establish an exhaustive invariant for all
Nyx input values across all later releases. Existing golden tests and
`check_docs.py`'s finite samples establish their results on the runtime where
they run, not every historical or future Python build.
[Python floating-point documentation](https://docs.python.org/3.14/tutorial/floatingpoint.html).
No interpreter installation, broad stability claim or runtime default is selected.

### Additive ruling questions and overlap with questions 1–7

These questions retain their original numbers and overlap references. Their
statuses now reflect rulings 1–6; observations above remain baseline evidence.

8. **Externally supplied payload text — Resolved by rulings 4 and 6; extends
   question 4.** Reject duplicate decoded keys and noncanonical private input;
   validate without replacing retained authenticated bytes. Human-facing
   conversion is upstream. Frozen projectors retain their contracts. Completing
   the canonical grammar remains question 4/O1, not a second acceptance-policy
   question here.
9. **Independent verification scope — Still open; extends question 7.** The six
   rulings specify behavior, not independent verification evidence. This needs
   maintainer scope and the independent reviewer's judgment. What parser and
   canonicalization independence must the evidence demonstrate, beyond record
   reconstruction with shared Python helpers, and what limits must accompany
   any resulting cross-language verification claim?
10. **Python runtime compatibility — Still open; extends questions 6/7.** The
    frozen-version boundary is settled and O1 excludes Python's serializer as the
    specification. Runtime coverage and evidence remain for maintainer selection
    and independent assessment. Which interpreter
    versions, implementations and value classes must satisfy byte compatibility,
    and what evidence is required before a runtime change can be treated as
    compatible with frozen commitments?
11. **Meaning of an unaffected corpus — Still open for evidence scope; extends
    questions 1/3/7.** Rulings 1–3 settle the numeric admission/preservation issues;
    that part of the former question is superseded by those rulings. The maintainer
    still selects the compatibility corpus and the independent reviewer assesses
    its coverage and claim limits. What population
    of retained records and fixtures must support a compatibility ruling, given
    float-free seed logs but float-bearing test state and a float-capable encoder?
    Absence in these two stores supplies no substitute for that evidence; it does
    not reopen the numeric rulings.

The nonfinite-token evidence now supports resolved question 3; exponent/17-digit/
negative-zero differences continue to inform open question 2/O1. Neither warrants
a duplicate ruling entry. O3 is the additional open JCS-alternative question,
rather than an unrecorded resolution of any question above.

## Float encoding specification

**Scope/status, 2026-09-14:** this is a compatibility specification of the current
finite-float wire behavior, not a seventh maintainer ruling. Rules F1–F5 below
state what an independent implementation must do to reproduce those bytes,
without consulting Python source. Their required outputs are relative to this
compatibility profile. They expose, rather than silently settle, O1's outstanding
new-codec confirmation and O3's explicit alternative. No different spelling or
algorithm default is selected, no gate is declared passed, and frozen projectors
"0", "1" and "2" keep their existing contracts.

This extraction follows the existing serializer-preservation requirement quoted
from Proposed ADR 0027 §3.1 above. It makes that behavior precise instead of using
"use Python's serializer" as a specification. The six MADE rulings remain in
force for the new codec. In particular, preserving a binary64 value does not
license silently approximating an exact-decimal input or a large integer.

**Probe baseline:** repository commit
`0655eba105851d5d9ab1d25cf6ee8a6eaad5af7a`, CPython 3.14.2, Windows AMD64.
The temporary `scratch/b2-float-encoding-probe.py` was executed and then deleted.
It loaded the actual `canonical_json` from `src/nyx/hashing.py:30`. It also
constructed decimal digits and notation separately using exact rational
arithmetic, without float `repr`, float formatting or JSON serialization in that
construction, and compared the resulting strings with the actual serializer.
All **19 table vectors plus 255 additional finite bit patterns matched**; each
serialized float also decoded back to its exact original 64 bits, including the
zero sign. This is bounded in-process compatibility evidence, not a foreign-language
decoder test, exhaustive binary64 proof or independent cryptographic review.

### Input and notation definitions

The input is a typed finite binary64 value, not a decimal string to be rounded
into one. In the vector table, hex is the 64-bit IEEE 754 encoding in most
significant byte first order, written as 16 hex digits. It is not a hexadecimal
floating-point literal. Let the sign bit be `s`, the 11-bit exponent field be `E`,
and the 52-bit fraction field be `f`. Its exact magnitude is:

- For `1 <= E <= 2046`: `(2**52 + f) * 2**(E - 1075)`.
- For `E = 0` and `f > 0`: `f * 2**(-1074)` (subnormal).
- For `E = 0` and `f = 0`: signed zero, handled by F4.

`E = 2047` is outside the finite domain and is excluded by MADE ruling 1.
For a nonzero input, apply F1 to its positive exact magnitude, then prefix a
single ASCII `-` iff `s = 1`. Positive values have no leading sign. Output uses
ASCII digits, `.` and, where required, `e` and the exponent sign; no whitespace,
locale punctuation, leading plus or trailing newline is emitted.

### F1. Digit selection and round trip

**Rule for byte-compatible output:** represent a positive decimal candidate as
`d = m * 10**q`, with positive integer `m` having no trailing zero and integer
`q`. Minimize the number of decimal digits in `m` among candidates that round to
the original binary64 under round-to-nearest, ties-to-even. Among equally short
candidates, select the one at the smallest exact distance from the binary64
value; if two are equally close, select the one with an even final digit in `m`.
Distance comparisons concern exact values, not rounded binary64 subtraction.
This describes Python's digit-selection requirements in
[Mark Dickinson's published explanation](https://discuss.python.org/t/faster-float-string-conversion-ryu/2466/12).

The normative requirement is shortest significant digits **and exact bitwise
round trip**, with the stated tie-breaks; a particular algorithm is only a means
of achieving it. This is the **shortest-round-trip binary-to-decimal conversion**
class, including Steele and White's **Dragon4** family and David Gay's `dtoa`
refinements. Implementations using another correct algorithm conform if they
satisfy these selection requirements and F2–F5's formatting rules. A library's
default presentation is not sufficient evidence of conformance.
[Steele and White, *How to Print Floating-Point Numbers Accurately*](https://fmt.dev/papers/p372-steele.pdf),
[David Gay's conversion work and publication](https://www.netlib.org/fp/).

"Shortest" here counts significant coefficient digits, not total JSON token
characters: signs, decimal-point placement, exponent syntax and the `.0` type
marker are governed separately. A round-trip-only test is insufficient to choose
unique bytes. Nor is repeatedly rounding the exact value to successively larger
decimal precisions a complete substitute for testing admissible shortest
candidates; the asymmetric-interval vector below exercises that distinction.

**Current serializer / probe / comparison:** F1 matches the current finite-float
output in the probe. For bit pattern `0000000000000001`, all five decimal strings
`3e-324` through `7e-324` decode to that same subnormal; the serializer selects
`5e-324`, the closest. For `430c6bf526340002`, both `1000000000000000.2` and
`1000000000000000.3` round back and have exactly equal distance from the input;
the serializer selects the even-final-digit form ending in `.2`. The exact-rational
probe asserted both facts. The table also covers a 17-significant-digit output
and the asymmetric `2**-24` case. No finite-byte departure is introduced by F1.

### F2. Exact positional/exponential thresholds

Let `D` be the decimal digits of F1's selected `m`, let `n = len(D)`, and define
the **selected decimal exponent** `e = q + n - 1`, so
`10**e <= d < 10**(e + 1)`. Use this selected decimal's exponent, not an
approximate floating-point `log10` of the input. This distinction accounts for
digit-selection carry across a power of ten.

**Rule for byte-compatible output:**

- Use positional notation exactly when **`-4 <= e < 16`**.
- Use exponential notation exactly when **`e < -4` or `e >= 16`**.

For positional notation put the decimal point after position `p = e + 1` in D:
if `p <= 0`, emit `0.`, then `-p` zeros, then D; if `0 < p < n`, insert `.`
after the first p digits; if `p >= n`, emit D, then `p - n` zeros, then `.0`.
These padding zeros are formatting, not additional significant digits in F1.
Zero itself is excluded from this exponent calculation and follows F4.

**Current serializer / probe / comparison:** these inequalities match Python's
current `repr` formatting used by the JSON serializer. The table contains the
predecessor, representative and successor binary64 values at each threshold.
The lower representative is the nearest binary64 to exact decimal `10**-4`
(that decimal is not exactly representable); its adjacent encodings straddle
the notation switch. The upper representative is exact `10**16`. Immediately
below it output is positional with `.0`; at it and immediately above it output
is exponential. The exact-rational formatter and actual helper agreed on all
these cases. No finite-byte departure is introduced by F2.

### F3. Exponent and significand spelling

**Rule for byte-compatible output:** when F2 selects exponential notation, emit
the first digit of D, followed by `.` and the remaining digits only if `n > 1`.
Do not add `.0` to a one-digit exponential significand. Then emit lowercase
ASCII **`e`**, followed by **`+` for a nonnegative exponent or `-` for a negative
exponent**, followed by the base-10 magnitude of e with **at least two digits**.
Pad a one-digit magnitude with one leading zero; otherwise add no padding.
There is no fixed three-digit width. No trailing significand zeros are appended.

**Current serializer / probe / comparison:** the probe generated `1e-07`,
`1e+16`, `1e+100` and the finite extremes with three-digit exponents. These
verify lowercase `e`, explicit positive sign and minimum two-digit padding.
The independent formatting construction matched the actual helper. No
finite-byte departure is introduced by F3. Omitting a positive sign, removing
the zero in `e-07`, emitting uppercase `E`, or adding `.0` before `e` would
depart from these bytes even when a decoder recovers the same value.

### F4. Signed zero

**Rule for byte-compatible output:** emit positive-zero bits `0000000000000000`
as **`0.0`** and negative-zero bits `8000000000000000` as **`-0.0`**. Never use
ordinary numeric equality with zero to discard the sign. Both are float tokens,
distinct from the true integer token `0`.

**Ruling boundary:** negative zero is **inside** ruling 3's preserved binary64
distinctions; it is finite, and collapsing its sign would violate that ruling.
The requirement to preserve the distinction is already MADE. The exact spelling
here specifies how the current compatible profile does it; it does not silently
turn O1's outstanding wire-profile confirmation into a new ruling.

**Current serializer / probe / comparison:** the two bit-pattern rows generated
`0.0` and `-0.0`; decoding and packing the result reproduced their different
64-bit patterns. Their object digests differ. F4 matches the serializer. A
negative-zero encoding of `0`, `0.0`, or `-0` would change bytes; `-0` also
decodes through Python's integer path and loses the binary64 zero sign.

### F5. Integral floats remain floats

**Rule for byte-compatible output:** never route a typed float through integer
encoding merely because its numerical value is integral. Under positional
notation, integral floats end with `.0`. Under exponential notation they keep
the exponent part; a single significant digit need not acquire a fractional
part. Consequently every finite float token has a `.` or an `e`, while an exact
integer uses its integer spelling without either. A decoder must retain that
type distinction rather than treating all JSON numbers as binary64 or converting
an integral float token into an integer. This complements ruling 2's exact-integer
preservation and the already quoted integer/float distinction in §3.1.

**Current serializer / probe / comparison:** probes confirmed true integer `1`
versus float `1.0`, and exact integer `10000000000000000` versus float `1e+16`.
The upper-threshold predecessor is integral and emits `9999999999999998.0`.
F5 matches the current serializer. Emitting bare `1` for float `1.0` would change
both the bytes and the decoded type. Integer range remains unanswered below.

### Generated conformance vectors for F1–F5

Every required output and digest below was generated by executing the probe,
not hand-transcribed as an expected constant. The float was constructed from its
binary64 bit pattern using `struct.unpack('>d', bytes.fromhex(bits))`.
The comparison formatter independently selected digits using exact `Fraction`
arithmetic and the F1 round-trip/tie-break conditions, then applied F2–F5.
For each row the probe asserted equality with `canonical_json(x)`, asserted
bitwise round trip through `json.loads`, and computed the digest from
`canonical_json({"value": x}).encode("utf-8")` with `hashlib.sha256`.

**Digest framing is exact:** hash the complete UTF-8 object
`{"value":<required output>}`, with no spaces, BOM or newline. The number is
not quoted. These are compatibility-vector digests, not a proposal for a new
payload hash formula or a sealed-body commitment. They differ from the earlier
scalar-token digests in this brief because the hash preimages differ.

"Smallest finite" is disambiguated by including the most negative finite value,
the smallest positive finite subnormal and the smallest positive normal. The
table is a generated conformance candidate for this compatibility profile; it
is not yet the frozen, independently reviewed B5 corpus.

| Case | Binary64 bits (hex) | Required output string (F1–F5; observed match) | SHA-256 of `{"value":<output>}` |
|---|---|---|---|
| Smallest positive finite / subnormal | `0000000000000001` | `5e-324` | `8f275eb622ce665f3cf21739b40600308dcea7c36627451f1c210a4152343c85` |
| Smallest positive normal | `0010000000000000` | `2.2250738585072014e-308` | `d4f55b1dc9e7cc034151fe75693c281a4cf27370127416c58c194ac0659e1110` |
| 17 significant digits | `3ff0000000000001` | `1.0000000000000002` | `156c932c6713198c5f24a01051d7e2e335842c1401a0fbb9ac1b488eeea7510e` |
| Negative zero | `8000000000000000` | `-0.0` | `c848a4efa987f46ba3bfd46242333afcb1c68c3240e0f35ae9d269b1c980648b` |
| Positive zero | `0000000000000000` | `0.0` | `d8b42cb220d5fd5974287c09df934755174112a8bea29ae02ca97dd50ea1d337` |
| Integer-valued float | `3ff0000000000000` | `1.0` | `3a7d647740ec6f86b72e0bf3948ab456551e07e9605e3a2785de1c66842ebb48` |
| Largest finite | `7fefffffffffffff` | `1.7976931348623157e+308` | `17579ea1287f0c7ed8799e2047914a528123a4c6fb86f604b1d37aa75b09303a` |
| Smallest finite (most negative) | `ffefffffffffffff` | `-1.7976931348623157e+308` | `4044b8207dfb123bf2b3d08cdb3772e056eff9707b60fd377495c6c8128c7f28` |
| Asymmetric round-trip interval (2**-24) | `3e70000000000000` | `5.960464477539063e-08` | `a20ad8d4989e0511d5471d1e930d78d4b27c29486b281c55fb7cb0b771b587a2` |
| Equidistant decimal choices | `430c6bf526340002` | `1000000000000000.2` | `9972d3e213ead86a7c11307db6d37b3367cd04be5405b9039c51189843792781` |
| Two-digit negative exponent | `3e7ad7f29abcaf48` | `1e-07` | `aece37dfda4992947222ea73b79996bba4aa181345a1fbb7f8c2b56b3fbd6a44` |
| Three-digit positive exponent | `54b249ad2594c37d` | `1e+100` | `f073ab151c720cbbf93e32b88655f2aff630e9a318395f8c8fd9c73a97f159fa` |
| Round-trip decimal-boundary carry | `44b52d02c7e14af6` | `1e+23` | `5add8f0ad0ac9f9e9fbd027279b5a7db972ab4d6219508a116d56f6db62677b3` |
| Lower threshold predecessor | `3f1a36e2eb1c432c` | `9.999999999999999e-05` | `800b498e075d3b2f172709aae7dbde15ba997b82f386fe42b7c789083d40b53c` |
| Lower threshold at | `3f1a36e2eb1c432d` | `0.0001` | `4e8c736958cd287696c5db2674af41fd38337bb6aa1a732bbfe5d3ff3063a809` |
| Lower threshold successor | `3f1a36e2eb1c432e` | `0.00010000000000000002` | `d7b48615d56897dd632ace9c804ddc2cc452eaeea5fe926322c484919abc4971` |
| Upper threshold predecessor | `4341c37937e07fff` | `9999999999999998.0` | `0f428644d976536a5cd8837e53170719604a311d00f64076a72adb5bd7fe1af0` |
| Upper threshold at | `4341c37937e08000` | `1e+16` | `f6b1d8095563fb7f57c554825c9d5402bfc8f69255edfaed38587394a2252515` |
| Upper threshold successor | `4341c37937e08001` | `1.0000000000000002e+16` | `b6007545839102d222b01e4af8aa59b386e4fa2aa1779d8f24f8073b06e1ea78` |

The additional sample used `random.Random(27).getrandbits(64)` for 256 draws,
omitting the one exponent-all-ones nonfinite pattern. Its 255 finite patterns
matched the exact-rational formatter and passed bitwise decode round trips.
The helper and `json.loads` still ran on the same Python interpreter; in
particular this does not independently validate Python's rational-to-binary64
conversion used by the comparison formatter. No cross-version stability claim
or exhaustive guarantee follows from 274 matches.

### Departures and questions still open

**Finite-format comparison:** all five rules reproduce the measured serializer;
no finite-format departure is specified. MADE ruling 1 remains a deliberate
new-codec departure from the legacy helper's nonfinite acceptance/output, as
established by the earlier probes. No source helper was changed. A future
different finite spelling changes canonical bytes and therefore hash preimages
(and, in the probed alternatives, hashes), so any explicit alternative or
migration must address compatibility; this work authorizes neither.

**O1 confirmation — unanswered, maintainer:** does the new codec adopt the full
current-compatible profile F1–F5, including shortest-candidate tie-breaks and
exact token/type spellings? The compatibility rules are now written down and
probed; this task does not itself mark the open wire choice MADE. Independent
review must still assess the specification and conformance evidence against the
pinned candidate; a shared-runtime probe is not that judgment.

**O3 alternative — unanswered, maintainer:** does explicit JCS adoption under a
new projector remain an available alternative if this specification's cost
dominates? No silent substitution is allowed. Any explicitly different contract
must account for the six MADE rulings and byte/hash compatibility. No additional
question about choosing a mandatory implementation algorithm is introduced:
within F1–F5, observable correctness, not algorithm identity, determines conformance.

### Numeric and resource bounds — unanswered ruling questions

These restate O2 and question 6; they do not duplicate them as new decisions.
Each requires the maintainer's ruling, with subsequent independent assessment of
the resulting protocol and evidence:

1. **Integer range — OPEN:** which exact integer values must every implementation
   admit, and what refusal behavior applies outside that range? No binary64 or
   host-integer bound is inferred; admitted integers must remain exact.
2. **String length — OPEN:** what maximum, measurement unit and rejection boundary
   apply to strings and object keys? No interpreter limit is adopted.
3. **Nesting depth — OPEN:** what maximum and counting convention apply to nested
   arrays/objects, and when must an input exceeding it be rejected?
4. **Total document size — OPEN:** what maximum and byte-counting boundary apply
   to a private document, and what refusal behavior is required before excessive
   resource use? No limit is chosen by these finite vector sizes.

The earlier remaining domain/API, compatibility-coverage and review questions
retain their recorded statuses. F1–F5 supply the current float format; they do
not close the whole private codec, B5 evidence, independent review or Gate 1.
