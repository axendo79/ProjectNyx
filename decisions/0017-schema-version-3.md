# ADR 0017: Database Schema Version 3

Status: Accepted

Date: 2026-09-09

Supersedes: [ADR 0016](0016-schema-version-2.md), only its selection of version `2` as the supported database schema version.

Related: [ADR 0013](0013-cross-belief-identity-semantics.md); [ADR 0015](0015-candidate-scoped-verification.md)

Implementation: Implemented in `schema.sql` and `src/nyx/storage.py`, including older-version refusal and schema-validation tests. Status updated 2026-09-11.

## Context

ADRs 0013 and 0015 require candidate records and identity relations. Adding them
continues to exercise ADR 0011's versioning contract; its refuse-and-preserve
policy applies unchanged.

## Decision

The database schema advances to version `3` for candidate records and identity
relations required by ADRs 0013 and 0015. Version `3` becomes the sole supported
version. The runtime enforces which version it supports; `schema_meta` is unchanged
in shape and does not gain a version-specific CHECK constraint.

Consistent with ADR 0011, no migration path is provided. Version-2 databases are
refused and left unchanged; the operator recreates them. All other initialization
and validation rules remain unchanged.

## Consequences

Further cross-belief stages may advance the database schema version again.

## Acceptance cases

- **Fresh initialization:** produces database schema version `3`.
- **Version-2 refusal:** a version-2 database refuses without mutation.
- **Validation:** ADR 0011's validation rules apply unchanged at version `3`.
