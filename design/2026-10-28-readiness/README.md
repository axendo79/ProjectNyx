# Nyx review and implementation-readiness handoff

**Status: review-only proposals; no implementation or authority change.**

Prepared against `cc7a0e336fe033bf8c054fd77725126765c92236`. This packet records
one bounded class-C finding, an unapplied fix with synthetic regression evidence,
and preparation for the first accepted ADR 0036/0037 implementation slice.
Normal test collection, source, schemas and authoritative records are unchanged.

## Report-reader error classification

**Open P3:** the initial candidate read in
[reports.py](../../src/nyx/reports.py), line 122 at the reviewed revision, occurs
outside the existing error normalization in `_detail`. Malformed projector-1
candidate JSON raises `JSONDecodeError`; a missing projector-2 candidate-map node
raises plain `ValueError`. Accepted
[ADR 0031 section 8(g)](../../decisions/0031-source-report-claims.md#g-named-reader-adapter-inputs-and-exact-return-shape)
requires `IntegrityError` for absent/inconsistent report provenance, while
reserving `KeyError` for an absent named candidate.

Both original failures refuse and return no report. This is an error
classification defect, not evidence of silent corruption, promotion or Layer A
mutation. No new semantic ruling is needed for the narrow conversion.

[reader-fix.patch](reader-fix.patch) adds five net lines around the candidate
storage read and a dedicated synthetic regression file. It preserves typed
integrity errors, exception causes, genuine missing-ID errors, invalid request
errors, supported versions and transaction ownership. The patch is **not applied**.
The proposed [test source](test_report_reader_errors.py.pending) stays outside
normal collection and imports no artifact-acquisition fixtures.

| Projector | Derived corruption | Transaction owner | Baseline | Patched isolated copy |
|---|---|---|---|---|
| `1` | Existing candidate JSON becomes `{` | Adapter | Intended assertion fails: `JSONDecodeError` | Pass: `IntegrityError` |
| `1` | Existing candidate JSON becomes `{` | Caller | Same intended failure | Pass |
| `2` | Referenced candidate-map root node missing | Adapter | Intended assertion fails: `ValueError` | Pass: `IntegrityError` |
| `2` | Referenced candidate-map root node missing | Caller | Same intended failure | Pass |

On Python 3.14.2, the exact proposed test produced four expected baseline failures
and four patched-copy passes. Every case first checks a valid synthetic report,
missing-ID `KeyError`, and exact invalid-input/unsupported-version `ValueError`.
Patched cases also check exception cause, transaction ownership and unchanged
Layer A. The test uses one synthetic mention/report and the existing fixed-clock
fixture. [reader-regression-results.json](reader-regression-results.json)
retains the shareable result summary and source fingerprints.

An earlier synthetic probe additionally checked contradictory input ordering,
pending-publication staleness, complete materialization equality with genesis
replay at a shared time, and identical reports after restoring the derived data.
These are focused local checks, not deployment or extraction-truth evidence.
No real store or external artifact was used. Runs used `-B`, disabled pytest
plugin autoload/cache, and isolated source/temp/output directories.

**Full repository pytest was not run for this packet.** The patch remains
unapplied; its four-case scratch result does not satisfy the full-suite requirement
for a later implementation. Publication checks cover documentation and patch
integrity. They do not activate the draft or certify unrun tests.

## Accepted next slice

[slice01.md](slice01.md) verifies the joint ADR 0036/0037 authority chain and
identifies the next narrow scope: slice 01 receipts and explicit selectors.
It separates accepted semantics, implementation permission and unavailable
acceptance artifacts. [slice01-acceptance.md](slice01-acceptance.md) and the
[newly authored pending draft](test_slice01_o3_selectors.py.pending) contain
limited signature/omission cases from explicit accepted API clauses. They were
not executed and are not recovered originals or complete replacement suites.

## Safe implementation pickup

For the reader fix, use a separately authorized writable implementation branch.
Read [AGENTS.md](../../AGENTS.md) and current files, verify the patch context with
`git apply --check`, retain the intended baseline failures, apply the narrow fix,
then run the focused test, required full suite and documentation checker. Update
the gap with actual evidence only after the implementation exists. Do not change
report versions, schemas, event hashes, or authority files.

For joint ADR 0036/0037, use the bounded [slice-01 prompt](slice01.md#safe-pickup).
The accepted records still require separate implementation authorization.
Neither this packet nor its publication supplies that authorization.

Illustrative commands for the later authorized reader implementation:

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_report_reader_errors.py
python -B -m pytest -q -p no:cacheprovider
python -B scripts/check_docs.py --fix-none
```

Inspect test execution and fixture scope before running these commands. Preserve
active data/process exclusions and report any incompatible validation requirement
instead of claiming it passed. No commit or push is implied for that future task.
