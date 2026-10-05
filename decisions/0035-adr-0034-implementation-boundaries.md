# ADR 0035: ADR 0034 Implementation Boundaries — Schema, Dependencies, Report Corrections

Status: Accepted — ratified by the maintainer, 2026-10-05; section 1 amended the same day for schema-5 committed-table constraints

Date: 2026-10-05

Implementation: Complete in (B) commits `82c3aa67a1327a1d9720afa973a2fa68a9c79c51`, `55f8ec295804be160ff987bccd16fffd29634831`, `8331f379ac3c118f5132489b881995020fb06a19`, `da060a98852acabbaf4c4452e215d96e4151045f` (schema 4/5 and migration including the committed-table amendment, the dependency check, and report-correction refusal), merged by PR #14 (`ecc1f36`).

Supersedes: [ADR 0025](0025-incremental-result-commitment.md)'s single supported database schema version, only as stated in section 1. [ADR 0034 section 6](0034-forward-state-transitions.md#6-correction-evidence)'s report mis-extraction route, only by deferring it as stated in section 3; its four evidence conditions remain the rule for that later decision.

Related: [ADR 0011](0011-database-schema-versioning.md), [ADR 0015](0015-candidate-scoped-verification.md), [ADR 0031](0031-source-report-claims.md), [ADR 0034](0034-forward-state-transitions.md)

## Context

The first implementation queue for ADR 0034 stopped on three gaps, correctly,
rather than guessing:

1. ADR 0034 requires database schema version 5, but did not supersede ADR 0025's
   rule that version 4 is the one supported version. Existing tests pin fresh
   creation at 4 and refuse 5.
2. ADR 0034 R9 requires an actual dependency check before a transition, but no
   accepted ADR says which recorded stage-two fields make a candidate dependent on
   another.
3. ADR 0034 section 6 requires report-correction evidence in `basis`, but supplies
   no basis shape for it.

This ADR closes each gap without changing any other part of ADR 0034.

## Decision

### 1. Schema versions 4 and 5

- Fresh initialization creates database schema version 5, which is version 4 plus
  the ADR 0034 relation table.
- Existing version-4 databases remain supported. They open unchanged for projectors
  "0", "1" and "2" and are never migrated implicitly.
- Projector "3" requires version 5. Selecting "3" on a version-4 database refuses
  without mutation.
- An explicit migration function converts a version-4 database to version 5 by
  adding the relation table and updating the metadata row in one transaction. It is
  for working copies (ADR 0034 section 10); no open, read or append path calls it.
- Every other version, including 0–3 and 6 and above, keeps ADR 0011's
  refuse-and-preserve behavior.

**Amendment, 2026-10-05: committed tables in schema 5.** In schema 4,
`committed_nodes` and `committed_roots` carry `CHECK (projector_version = '2')`.
In schema 5 both constraints are `CHECK (projector_version IN ('2', '3'))`, so
version-"3" committed rows are stored in the same tables, isolated by
`projector_version` as ADR 0034 section 1 requires. No other table definition
changes. Because SQLite cannot alter a CHECK constraint in place, the explicit
migration rebuilds exactly these two tables inside its single transaction (create
the schema-5 table, copy every row unchanged, drop the old table, rename),
verifies that every copied row is identical, and rolls back entirely on any
failure. No new committed tables are added and the relation table is not
repurposed.

Existing tests that pin fresh creation at version 4, or refuse version 5, change
their expectations to this rule. Event bytes, hashes, lineage and derived results
under projectors "0", "1" and "2" must not change on either schema version;
fixtures that pin only the fresh schema version or its table list are updated.

### 2. Dependency check for transitions (ADR 0034 R9)

Stage two creates only ordinary candidates: a `direct_observation` verification
basis, empty `predecessors`, empty `restrictions` and empty `opposing_events`.
ADR 0015 section 5's dependent approvals and restrictions have no stage-two
producer. The check is therefore closed over these recorded fields.

Before any correction, replacement or expiry, at the locked pre-event snapshot,
the transition refuses before append if either holds:

- any target has a `verification_basis` kind other than `direct_observation`, or a
  nonempty `predecessors`, `restrictions` or `opposing_events`;
- any candidate in the snapshot names a target in its `predecessors` or
  `restrictions`.

The refusal raises `NotImplementedError` naming ADR 0015 section 5, the same
fail-loud pattern as other undecided transitions. Replay applies the same check.

The fresh candidate recorded by a projector-"3" correction or replacement is
ordinary in this sense: its verification basis is `direct_observation` from its
own event, with empty `predecessors`, `restrictions` and `opposing_events`. It is
therefore an eligible target for a later transition. A target's own
`superseding_events` is governed by ADR 0034's live-status rule, not by this check.

### 3. Report corrections deferred

A candidate is report-scoped when its recorded `source.config` contains
`report_vocabulary` (ADR 0031). Every correction whose targets include a
report-scoped candidate refuses before append, and replay refuses the same.
Replacement and expiry already refuse report-scoped targets (ADR 0034 section 5).

The report-correction basis shape and the correction-evidence admission mechanism
are decided together with the first extractor admission, under ADR 0034 section
6's four conditions. Until then no report correction is possible, which matches the
empty admission list ADR 0034 ratified.

## Acceptance cases

- Fresh schema 5 accepts version-"3" committed node and root rows and refuses
  any other version; migration of a version-4 copy rebuilds both tables with
  identical rows, and an injected failure leaves the copy at version 4 unchanged.
- Fresh creation records version 5; a version-4 database opens for "0", "1" and
  "2" with identical results and unchanged bytes; selecting "3" on it refuses
  without mutation; explicit migration of a copy yields version 5 and leaves the
  source untouched; versions 0–3 and 6 refuse unchanged.
- A target with a non-`direct_observation` basis, or nonempty `predecessors`,
  `restrictions` or `opposing_events`, refuses. A candidate naming a target in its
  `predecessors` or `restrictions` makes the transition refuse. Ordinary targets
  pass, and the check demonstrably ran on them.
- A correction's fresh candidate is ordinary and can itself be replaced, corrected
  or expired.
- Any correction including a report-scoped target refuses before append, with
  count and tip unchanged; a recorded one refuses at replay.
