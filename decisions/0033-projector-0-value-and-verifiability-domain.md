# ADR 0033: Projector 0 value and verifiability domain

Status: Accepted — ratified by the maintainer, 2026-09-28

Date: 2026-09-28

Implementation: None

Supersedes on acceptance: No accepted value-type rule. This defines legacy submission admission without changing historical projection semantics, serialization, or stage-two validation.

Related: [ADR 0001](0001-observation-recorded-resolves-to-verified.md), [ADR 0002](0002-payload-stored-plaintext-in-v0.md), [ADR 0004](0004-correction-appended-supersedes-via-superseding-events.md), [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0024](0024-no-authoritative-head.md), [ADR 0030](0030-sole-writer-and-positional-fields.md), [ADR 0032](0032-explicit-stage-two-projector-selection.md).

## Context

The maintainer supplied these NYX_ERROR_REPORT reproductions, restated in the
2026-09-28 drafting request:

- **F3:** a non-scalar legacy value, such as a list or object, can enter Layer A
  and then fail SQLite binding during projector-"0" publication. The committed
  event remains in the append-only log and permanently blocks publication past
  that event; rejecting it only during publication is too late.
- **F4:** a numeric legacy value materializes through SQLite TEXT affinity and
  reads back as text, while projector-"0" replay retains the JSON number. The
  materialized and replayed values therefore differ in type.

These are the maintainer's supplied findings, not new reproductions performed by
this authority-only drafting task. They motivate an admission decision, not a
repair or reinterpretation of existing events.

The [V0 schema](../spec/NYX_V0_IMPLEMENTATION.md), section 4, declares
`resolved_beliefs.current_value TEXT` (line 175 at drafting). Its section 6
acceptance example uses `current_value="64GB"` (line 272). The
[architecture](../spec/NYX_ARCHITECTURE.md), section 2's legacy support-set example,
also uses `"current_value": "64GB"` (line 133). All five input values in
[the legacy fixture](../tests/fixtures/version0_ordinary.json) are strings, and
its `expected_canonical` projection contains string values.
The column declaration and examples do not themselves define the submission's
value type. No accepted sentence admitting arbitrary JSON values or requiring a
different legacy value type was found.

[ADR 0002](0002-payload-stored-plaintext-in-v0.md) specifies canonical JSON
payload storage, and [ADR 0014 section 6](0014-cross-belief-reducer-and-hash-lineage.md#6-canonical-serialization)
specifies serialization without normalizing recorded values. Neither chooses
the domain of this legacy payload field. This proposal preserves those rules.

## Proposed decision

### 1. Scope

These admission rules apply only to projector `"0"` (legacy) submissions,
including its supported observations and corrections through ordinary submissions
and low-level retained-pair appends. Projectors `"1"` and
`"2"` retain their current validation. This proposal changes no event type,
origin-to-state mapping, correction semantics, projector selection, or hash rule.

### 2. Value domain and refusal boundary

`value` must be a JSON string, represented by Python `str` after decoding.
The empty string `""` is allowed. This is a type rule only, with no content
policy: no nonempty requirement, coercion, normalization, or content filter is
introduced for `value`.

Every other JSON type is refused: number (integer or floating-point), boolean,
null, array/list, and object/dict. Validate at all three refusal boundaries:

- Immune Stage 1 ([`immune.stage1_schema_validate`](../src/nyx/immune.py)).
- The projector-`"0"` branch of
  [`storage.append_submission`](../src/nyx/storage.py), before `writer.assign`.
- The shared legacy append path, `storage._append_legacy_locked`, before
  insertion into Layer A. Both `append_submission` and the public
  `storage.safe_append_event` use this path for projector `"0"`.

Each boundary independently raises `integrity.IntegrityError` for a disallowed
value. `safe_append_event` reaches the shared legacy append path without running
Stage 1 or `append_submission`; its safety must not depend on either earlier
check or on caller validation. The public low-level API is used by
[`scripts/probe_lineage_scaling.py`](../scripts/probe_lineage_scaling.py).
Refusal leaves Layer A unchanged: its event count and tip event hash are both
identical before and after the attempt.

The Stage 1 required-field check must distinguish a present empty-string value
from a missing field; it must not reject `""` as missing. A present JSON null is
a disallowed value type and must receive the typed refusal above.

### 3. Verifiability domain

`verifiability` must be exactly one of:

- `"externally_checkable"`
- `"locally_checkable"`
- `"subjective"`
- `"structurally_unverifiable"`

This is the existing stage-two domain in [`reducer.reduce`](../src/nyx/reducer.py):
inside the observation claim loop, the `if claim["verifiability"] not in (...)`
guard lists these four strings and raises `ValueError("unknown verifiability")`
(around line 229 at drafting). Architecture section 2's two-dimensional-state
enumeration lists the same values. Stage-two code and its error behavior remain
unchanged.

Enforce this domain at the same three legacy boundaries as the value check,
raising `integrity.IntegrityError` before append for any other value, with the
same unchanged event-count and tip-hash guarantees. This validates the supplied
label; it does not infer verifiability or change verification-state assignment
under ADR 0001.

### 4. Existing logs

Replay semantics remain unchanged. Do not apply these new submission checks to
historical replay or introduce retroactive rejection of committed events.
[`scripts/verify_store.py`](../scripts/verify_store.py) retains its
`Replay.legacy` TEXT-affinity handling: the block beginning
`# SQLite TEXT affinity is part of the shipped legacy representation.` casts
historical numeric values with `SELECT CAST(? AS TEXT)` when comparing against
materialization (around lines 386-388 at drafting).

Nothing is rewritten: no Layer A events, payloads, timestamps, hashes, or existing
materialized values are converted or repaired. This proposal does not make an
already publication-blocking event publishable. The legacy fixture's frozen
projection bytes and existing historical numeric replay behavior remain intact.

## Proposed acceptance cases

For every refusal below, use an otherwise valid legacy submission against a
published store with a known tip. Exercise all three refusal boundaries
separately: Stage 1; projector-`"0"` `append_submission`, bypassing Stage 1; and
projector-`"0"` `safe_append_event`, bypassing both Stage 1 and
`append_submission` to exercise `_append_legacy_locked`. For the low-level API,
build an otherwise valid retained Envelope / Payload pair with correct hashes
and append position, so the domain check is the reason for refusal. Assert
`integrity.IntegrityError`, the same Layer A event count, and the same tip event
hash after each refusal. An exception assertion alone is insufficient. Cover
both supported legacy value-setting submission kinds.

| Case | Example `value` | Required result at each boundary |
|---|---|---|
| Integer number | `42` | IntegrityError; event count and tip hash unchanged. |
| Floating-point number | `1.5` | IntegrityError; event count and tip hash unchanged. |
| Boolean | `true` and `false` | IntegrityError; event count and tip hash unchanged. |
| Null | `null` | IntegrityError; event count and tip hash unchanged. |
| Array/list | `[]` | IntegrityError; event count and tip hash unchanged. |
| Object/dict | `{}` | IntegrityError; event count and tip hash unchanged. |
| Empty string | `""` | Accepted by Stage 1, `append_submission`, and `safe_append_event`; publication/read/replay preserve the empty string. |

- **Verifiability refusal:** with a valid string value, reject `"bogus"` and
  non-string verifiability inputs at all three legacy boundaries with IntegrityError,
  unchanged event count, and unchanged tip hash.
- **Accepted strings and labels:** accept `"64GB"` and `""` with each of the four
  verifiability labels; preserve the exact value and supplied label through
  append, publication, and replay under the existing origin/state rules.
- **Historical numeric compatibility:** build the numeric legacy log fixture by
  direct insertion below the new admission checks, since no such store exists.
  Do not construct it through Stage 1, `append_submission`, or `safe_append_event`,
  which must refuse new numeric values. Retain numeric values in replay and
  TEXT-affinity materialized reads;
  the standalone verifier still applies its historical numeric comparison.
  Assert no rewriting of the existing log or materialization.
- **Version isolation and frozen bytes:** retain the legacy golden fixture and
  stage-two validation behavior unchanged. No new legacy admission rule is
  installed in a stage-two reducer or historical replay path.

## Ratification and implementation

The maintainer ratified this ADR on 2026-09-28. This authority change implements
nothing. After the maintainer commits the authority change and confirms that
commit under [AGENTS.md](../AGENTS.md), implementation proceeds as a separate
(B) change.
