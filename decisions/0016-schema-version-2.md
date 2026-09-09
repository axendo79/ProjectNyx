# ADR 0016: Database Schema Version 2

Status: Accepted

Date: 2026-09-09

Supersedes: [ADR 0011](0011-database-schema-versioning.md), only its selection of version `1` as the supported database schema version.

Related: [ADR 0014 section 8](0014-cross-belief-reducer-and-hash-lineage.md#8-append-freshness-and-derived-progress)

Implementation: Pending; implementation is a separate task.

## Context

ADR 0014 requires a separate derived-progress record. Adding it is the first
exercise of ADR 0011's versioning contract; its refuse-and-preserve policy applies
unchanged.

## Decision

The database schema advances to version `2` to add the derived-progress record
required by ADR 0014 section 8. Version `2` becomes the sole supported version.
The runtime enforces which version it supports; `schema_meta` is unchanged in
shape and does not gain a version-specific CHECK constraint.

Consistent with ADR 0011, no migration path is provided. Version-1 databases are
refused and left unchanged; the operator recreates them. All other initialization
and validation rules remain unchanged.

## Consequences

Further schema changes for cross-belief work, including candidate records and
identity relations, are later stages and will advance the database schema version
again.

## Acceptance cases

- **Fresh initialization:** produces database schema version `2`.
- **Version-1 refusal:** a version-1 database refuses without mutation.
- **Validation:** ADR 0011's validation rules apply unchanged at version `2`.
