# Joint ADR 0036/0037 slice 01 preparation

**Review only. No authority, source, schema or normal-test activation.**

## Authority and current implementation

The accepted records and local Git ancestry were verified against
`cc7a0e336fe033bf8c054fd77725126765c92236`.

| Record | Authority commit | Scope | Standing |
|---|---|---|---|
| [ADR 0036](../../decisions/0036-strict-payload-keys.md) | `50297d7d53e88b2442ab3f5844e7e7bac5fb071a` | ADR 0036 and narrow ADR 0035 section-1 amendment | Accepted; Implementation None |
| [ADR 0037](../../decisions/0037-o3-mention-discovery.md) | `1bf92a60fc7abb85614bf0b1783f754b2204c34b` | ADR 0037 only | Accepted; Implementation None |

Both commits are ancestors of the reviewed HEAD: both local
`git merge-base --is-ancestor` checks returned 0. Git records both commit dates
as 2026-10-23; the accepted text records ratification on 2026-10-22. These are
distinct dates. This verifies local content/history, not cryptographic authorship
or a separate instruction authorizing implementation.

The shareable [authority summary](authority-verification.json) records those
checks without machine-local paths or unrelated run evidence.

[ADR 0036 V9](../../decisions/0036-strict-payload-keys.md#v9-ratification-and-delivery-dependency)
says no unanswered drafting choice remains in the joint scope and explicitly
requires separate implementation authorization. Both ratification paragraphs
retain the [25-slice dependency plan](../2026-10-14-adr-0036-0037-implementation-plan.md).
That older non-authoritative plan still says Proposed; the later Accepted status
markers govern standing. It supplies dependency ordering, not missing authority.

Preserve [ADR 0032](../../decisions/0032-explicit-stage-two-projector-selection.md)'s
exact legacy defaults/aliases, ADRs 0034/0035's existing semantics, and
[ADR 0031](../../decisions/0031-source-report-claims.md)'s specialized report
`1`/`2` guards. Shared V2 explicitly preserves those report guards.

## Intended surfaces and slice boundary

| Surface | Intended bounded work | Not authorized by this slice |
|---|---|---|
| [test_explicit_projector_selection.py](../../tests/test_explicit_projector_selection.py), allowlists and AST guard | Inventory all real selectors; reuse existing checks for parameter/class/parser defaults and omission before work | New legacy exceptions or hidden defaults |
| [projection.py](../../src/nyx/projection.py) registry; [storage.py](../../src/nyx/storage.py) dispatch/schema/opening; [package constants](../../src/nyx/__init__.py) | Record independent current/future version axes and actual future entry points | Enabling projector `4`, changing frozen envelope defaults, creating schema 6 |
| [ingestion.py](../../src/nyx/ingestion.py), [writer.py](../../src/nyx/writer.py), [skeleton.py](../../src/nyx/skeleton.py), later command parsers | Inventory preparation/submission boundaries for explicit selector refusal before work | Guessing strict helper names or implementing parser/append/retry semantics |
| ADR 0037 O2 operations | Exact names/signatures for `list_subjects`, `list_mentions`, `find_mention`, `list_properties`, `list_beliefs`; keyword-only inputs after connection; required `projector_version` | Query/index/readiness behavior from later slices |
| ADR 0037 O9 `replay_discovery` | Inventory its explicit keyword-only historical signature | Historical execution, which belongs to slice 20 |
| [reports.py](../../src/nyx/reports.py) and [report_importer.py](../../src/nyx/report_importer.py) | Keep specialized guards unchanged | New report producer or reader version |

The seven accepted identifiers are projector `4`, envelope schema `1`,
lineage `nyx-belief-lineage/4`, database schema `6`, index `nyx-o3-index/1`,
response `nyx-o3-page/1`, and cursor `nyx-o3-cursor/1`. Inventory is not activation.
Module placement, strict helper names and thin test bindings remain implementation
details; this packet does not turn proposed names into requirements.

Slice 01 precedes schema layout/opening/migration (02–04), predicate/append/
preparation/retries (05–08), raw-aware projector and equivalence (09–10),
membership/readiness/enrollment/publication/queries/history (11–20), and the
later independent verification/diagnostic/copy/crash/work-counter slices (21–25).
Do not create successful stubs to make early signature cases look complete.

## Unavailable drafts and replacement scope

The exact ignored paths named by the plan were unavailable in the reviewed
checkout:

- `scratch/pending-tests/test_adr0036_strict_payload_keys.py.pending`
- `scratch/pending-tests/test_adr0037_o3_discovery.py.pending`

Targeted reads returned path-not-found. No broader worktree/private search was
performed. The plan's function/parameter counts are historical planning numbers,
not available, collected or passing cases.

The plan names four slice-01 witnesses: joint maintainer authority receipts,
version identifiers/selector signatures, strict selection before work, and new
O3 selector guards. Integrated identifier/schema assertions also depend on slice
02; runtime guards need real future entry points. Record subcase status honestly.
Keep later cases parked; no skip/xfail or broken normal suite is a delivery shortcut.

[slice01-acceptance.md](slice01-acceptance.md) is a newly authored clause-to-case
checklist. [test_slice01_o3_selectors.py.pending](test_slice01_o3_selectors.py.pending)
is a limited new draft for explicit O2/O9 signatures and omission guards.
Neither is a lost original, an executed test, or a complete replacement suite.
Its fixture names are adapter vocabulary only. Bind real production behavior;
never fabricate counters, refusals or success. Unsupported-selector outcome
representation and strict helper names are deliberately not invented.

## Readiness and remaining conditions

- Accepted semantics suffice for the bounded receipt/selector scope; no new
  semantic ruling is identified here.
- Separate implementation authorization is still required. Publication of this
  review packet does not supply it.
- Missing acceptance artifacts must be recovered from an authorized source or
  deliberately recreated from accepted clauses with clear new provenance.
- Full pytest and documentation checks remain required for later applied
  implementation. This review did not run the new draft or a full suite.
- Proposed ADRs 0027–0029, erasure/private-codec work, usage/Dream persistence,
  report corrections, merge/split and support attachment remain outside scope.

## Safe pickup

> In an approved writable implementation branch, prepare or, only after explicit
> implementation authorization, execute joint ADR 0036/0037 slice 01. Read
> AGENTS.md and current Accepted/Implementation markers, verify the authority
> commits above, and preserve ADR 0032's exact allowlists. Inventory actual
> selectors and version axes against 0036 S1/V1/V9 and 0037 O2/O7/O9. Recover the
> missing parked tests from an authorized source or recreate accepted cases with
> explicit newly-authored provenance. Bind only real production functions. Keep
> integrated/later cases parked until dependencies exist; do not enable later
> schema/projector/query behavior or fabricate successful stubs. After authorized
> implementation, run required full pytest and docs checks when allowed and
> report actual evidence. Preserve frozen contracts and all active data/process
> exclusions. Do not edit spec/decisions or infer commit/push permission for that
> future task.
