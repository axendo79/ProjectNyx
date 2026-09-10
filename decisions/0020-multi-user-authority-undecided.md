# ADR 0020: Multi-User Authority Remains Undecided

Status: Accepted

Date: 2026-09-09

Related: [ADR 0014 section 1](0014-cross-belief-reducer-and-hash-lineage.md#1-snapshot-read-contract); [ADR 0015](0015-candidate-scoped-verification.md); [ADR 0019 section 4](0019-identity-bootstrap.md#4-association-with-an-existing-subject-requires-an-admissible-basis)

Implementation: Dependent implementation is blocked pending later decisions.

## Context

Multiple contributors under one acceptance policy are distinct from multiple
authorities each controlling identity decisions or verification outcomes. The
term "multi-user" does not settle which model applies. This boundary records
the unresolved choice without selecting either model.

## Decision

Multi-user participation and authority semantics for v1 remain undecided.
Existing source attribution implies no ownership, authorization, independent
corroboration, or user-specific verification. actor_id records provenance and
supplies no authorization policy.

Authority over intended reference is not authority over shared identity. A
speaker may clarify what they meant; that does not authorize reinterpreting
another speaker's mention, changing a shared entity's membership, or transferring
another's evidence. This gap exists with one operator because the log can contain
other speakers' assertions.

Permission to make a change and evidence that a relationship holds are separate
requirements. A ratified admissible basis under ADR 0019 section 4 must state
what relationship the evidence establishes, whose assertions or records it
concerns, and what change the actor may authorize.

Whatever authority model is later chosen must supply reproducible historical
authorization. Replay must not consult current permissions to decide whether an
earlier identity event was valid, consistent with ADR 0014 section 1's pre-event
snapshot contract.

## Consequences

Dependent implementation remains blocked. Fixtures must not make every actor
authoritative or install an implicit owner. Later decisions must explicitly
resolve the authority assumptions on which they depend. This ADR selects no
roles, ownership rules, permission scheme, or user-specific verification model.

## Acceptance cases

- **Participation is not authority:** adding a second contributor does not
  silently select either one shared acceptance policy or separate authorities.
  Implementation depending on that choice remains blocked.
- **Attribution supplies no privileges:** an actor_id alone establishes none of
  ownership, authorization, independent corroboration, or user-specific
  verification. Fixtures do not grant these by actor identity or operator status.
- **Reference clarification stays scoped:** a speaker's clarification does not
  authorize changes to another speaker's mention, shared entity membership, or
  another's evidence. A single-operator fixture containing both speakers does
  not bypass this boundary.
- **Admissible basis is complete:** a proposed basis naming evidence but omitting
  the relationship, affected assertions or records, or the actor's authorized
  change does not satisfy this boundary. Permission alone likewise does not
  establish the relationship; dependent implementation remains blocked.
- **Historical authorization is reproducible:** a later authority model must
  reproduce authorization at the pre-event prefix. Changing current permissions
  cannot substitute for that historical determination during replay.
- **No fixture defaults:** tests requiring unresolved authority semantics remain
  blocked rather than supplying universal authority or an implicit owner.
