# ADR 0032: Explicit Stage-Two Projector Selection

Status: Accepted — maintainer acceptance 2026-09-23

Date: 2026-09-22

Implementation: Complete in commit `55b5af0e8fefbf71a55adcf4a89f4e6464094584`: explicit stage-two parameters, required lineage-probe selection, the AST regression guard, and caller updates preserving previous versions.

Supersedes: [ADR 0025 section 1](0025-incremental-result-commitment.md#1-version-and-semantic-scope), only “Existing API defaults remain unchanged” for selectable stage-two defaults under the invariant below. Explicitly allowlisted legacy default-"0" boundaries, frozen projected bytes and semantics remain unchanged.

Related: [ADR 0010](0010-projection-parameters.md), [ADR 0014](0014-cross-belief-reducer-and-hash-lineage.md), [ADR 0023](0023-stage-two-contract.md), [review E2 and R1](../design/2026-09-22-review-and-next-steps.md).

## Context and evidence

At the inventory commit, several stage-two preparation, publication, recovery,
snapshot and read entry points silently chose projector “1” on omission.
ADR 0025 preserved those defaults until this explicit partial supersession.

The review's E2 table was supplied reviewer evidence. Step 0 has now measured
the same workload shape locally: one mention plus five single-claim observations
per subject, with fixed 200-byte values. The
[recorded probe output](../design/2026-09-22-store-scaling.json) and
[README measurement description](../README.md) record Python 3.14.2 / Windows 11,
one independent fresh-store sample per measured scale:

| Projector | Events | Ingestion seconds | Verifier seconds |
|---|---:|---:|---:|
| 1 | 300 | 10.502508 | 0.093599 |
| 1 | 600 | 37.988647 | 0.255254 |
| 1 | 1200 / 2400 | explicitly capped | not run |
| 2 | 300 | 2.434998 | 1.341488 |
| 2 | 600 | 6.673959 | 4.335636 |
| 2 | 1200 | 12.061119 | 14.838082 |
| 2 | 2400 | 24.545916 | 48.101215 |

The probe and verifier fix are committed in f8dd633. These are measurements of
that implementation/workload, not universal throughput guarantees or exact
reproductions of the supplied review's fixture IDs. Projector “1” ingestion
grew about 3.62 times when events doubled from 300 to 600. Removing one verifier
copy bottleneck did not make total projector-“2” verification linear. Neither
observation changes correctness or authorizes silently upgrading a caller.

Requiring an explicit choice makes the cost and version contract the caller's
decision. This decision chooses no replacement default, deprecates no supported
version, and does not change the log or reduction semantics.

## Decision

### 1. Invariant and implementation inventory

**No selectable stage-two projector default may exist in `src/` or `scripts/`
outside an explicit legacy-projector-"0" allowlist.** This governs public and
private functions, constructors, wrappers, diagnostic parsers and future code;
the inventory below is evidence, not the limit of the rule.

1. **Naming rule:** any new parameter that selects a projector version in src/
   or scripts/ must be named `projector_version`. Existing selectors under other
   names are grandfathered only as enumerated in item 3 below. No new alias may
   be added without an ADR amendment. This does not reserve `version` or
   `projector` for projector use or restrict unrelated parameters.

2. **Mechanical guard:** walk all Python ASTs under src/ and scripts/. Every
   parameter named `projector_version` with a default fails unless its file and
   qualified function name are on ADR section 3's legacy default-"0" function list
   and its default is the literal string "0". This covers positional and keyword-only parameters,
   constant-valued and arbitrary-expression defaults, private and nested
   functions, and future functions.

   The guard also checks class-level annotated fields named `projector_version`.
   Such a field fails if it has a default, unless the default is
   `field(..., init=False)`, which is not a constructor parameter;
   committed.Snapshot.projector_version is the existing instance. This closes
   defaults introduced through generated dataclass constructors, which have no
   `def` to inspect.

3. **Enumerated existing aliases:** each entry is identified by file, qualified
   function name and parameter name. The test checks that every listed function
   and parameter exists; a rename or removal fails rather than silently dropping
   coverage.

   **3a. Legacy default aliases:** each must default to the literal string "0".

   | File | Qualified function name | Parameter |
   |---|---|---|
   | scripts/seed_store.py | seed_store | projector |
   | scripts/verify_store.py | verify_store | projector |

   **3b. Required aliases:** each must have no default. Adding any default,
   including literal "0", fails the test.

   | File | Qualified function name | Parameter |
   |---|---|---|
   | src/nyx/storage.py | _append_stage_two | version |
   | src/nyx/storage.py | _registered_projector | version |
   | src/nyx/storage.py | _snapshot_projector | version |
   | src/nyx/storage.py | _read_snapshot | version |
   | src/nyx/storage.py | _read_identity | version |
   | src/nyx/storage.py | _publish_delta | version |
   | src/nyx/cli.py | _identity_version | version |
   | src/nyx/cli.py | _replay | version |
   | scripts/verify_store.py | Report.__init__ | version |
   | scripts/verify_store.py | load_projection | version |
   | scripts/verify_store.py | lineage_record | version |
   | scripts/verify_store.py | Replay.__init__ | version |
   | scripts/verify_store.py | verify_connection | version |

4. **No renames:** the separate implementation (B) change renames no selectors.
   It implements the guard with the complete alias enumeration above and removes
   _append_stage_two's default while retaining its `version` parameter name.

Argparse `--projector-version` must be declared required=True with no default
wherever it appears. `--projector` is permitted only at the three legacy parser
allowlist entries in ADR section 3 (src/nyx/cli.py, scripts/seed_store.py,
scripts/verify_store.py), each with literal default "0"; any other occurrence of
`--projector` fails. Matching is on exact option strings, not prefixes: options
that merely begin with `--projector`, such as scripts/probe_store_scaling.py's
`--projector-1-max-events`, are outside this rule.

The (B) guard test must assert that `--projector-1-max-events` passes exact-string
parser matching, that committed.Snapshot's non-constructor `projector_version`
field passes, and that a synthetic dataclass field `projector_version: str = "1"`
with init=True fails.

The guard enforces the naming rule and explicit enumeration mechanically within
that stated coverage; it does not detect a projector selector hidden under an
unlisted name. Review covers that case. Unrelated `version` or `projector`
parameters are outside this guard's scope.

The following inventory is at commit `9bd9a04` (before this implementation).
These callable signatures default projector_version to “1”.
The reducer constructor uses PROJECTOR_VERSION, whose value is “1”. No callable
signature in src/ or scripts/ defaults that argument to “2”.

| File | Function or method | Default at 9bd9a04 |
|---|---|---|
| src/nyx/ingestion.py | prepare_observation | projector_version="1" |
| src/nyx/ingestion.py | submit | projector_version="1" |
| src/nyx/projection.py | project_snapshot | projector_version="1" |
| src/nyx/reducer.py | Snapshot.__init__ | projector_version=PROJECTOR_VERSION (“1”) |
| src/nyx/skeleton.py | _record_stage_two | projector_version="1" |
| src/nyx/skeleton.py | record_mention | projector_version="1" |
| src/nyx/storage.py | read_snapshot | projector_version="1" |
| src/nyx/storage.py | _read_record | projector_version="1" |
| src/nyx/storage.py | read_identity_status | projector_version="1" |
| src/nyx/storage.py | read_entity_status | projector_version="1" |
| src/nyx/storage.py | read_mention_status | projector_version="1" |
| src/nyx/storage.py | read_entity_link_status | projector_version="1" |
| src/nyx/storage.py | read_entity | projector_version="1" |
| src/nyx/storage.py | read_mention | projector_version="1" |
| src/nyx/storage.py | read_entity_link | projector_version="1" |
| src/nyx/storage.py | read_claim_candidate | projector_version="1" |
| src/nyx/storage.py | read_claim_candidate_value | projector_version="1" |
| src/nyx/storage.py | read_belief_scalar | projector_version="1" |
| src/nyx/storage.py | lookup_current_belief_id | projector_version="1" |
| src/nyx/storage.py | materialize_pending | projector_version="1" |
| src/nyx/storage.py | rebuild_projection | projector_version="1" |
| src/nyx/storage.py | read_belief_status | projector_version="1" |
| scripts/probe_lineage_scaling.py | sample | projector_version="1" |

Two additional implicit selections are part of the explicitly enumerated scope:

| File | Function | Selection to remove |
|---|---|---|
| src/nyx/storage.py | _append_stage_two | At 9bd9a04 the equivalent argument is version="1". Remove its default in (B); retain the version name as an existence-checked required alias in item 3b. |
| scripts/probe_lineage_scaling.py | main | Its signature has no version argument, but its argument parser supplies --projector-version default="1". Require that diagnostic option so main cannot hide omission from sample. |

The test-local wrapper
tests/test_seed_store.py::test_fixture_is_deterministic_and_uses_ingestion.record_submit
also defaults projector_version to “1”. It must mirror submit's required
argument during implementation; it is not a public entry point or an additional
production contract.

projection.Snapshot is the imported reducer.Snapshot, not another implementation.
committed.Snapshot.projector_version is a fixed dataclass field with init=False,
not a selectable argument default. The explicitly version-specific
committed_storage helpers and reducer implementations have no version-selection
argument to remove. ingestion.prepare_mention constructs a version-independent
event pair and selects no projector. These are not hidden “2” defaults.

### 2. Missing selection refuses

For every selectable stage-two boundary outside section 3's explicit allowlist,
the caller must provide the projector version.
Omission refuses before any database initialization, append, publication,
recovery, snapshot/read work or event preparation. A required Python argument
may provide the refusal; a diagnostic parser may require its option. No omitted
value, None, latest-version lookup, newest-version fallback or environment
inference substitutes a default.

Existing explicitly supplied supported versions retain their existing behavior.
Unknown versions still refuse under ADR 0010. This decision does not broaden
which versions any function supports or turn a version-specific snapshot into
a generic implementation. A signature change may make a parameter keyword-only
where necessary to keep it required without inventing a sentinel default;
implementation must update the corresponding explicit call sites.

All internal callers, wrappers, tests and examples must state their intended
version. Existing version-“1” callers must not silently move to “2” as part of
adding the argument. Deliberately changing a caller's selection remains a separate,
reviewable choice.

### 3. Legacy and other boundaries preserved

Version “0”, its supported events, projector bytes and defaults are unchanged.
In particular, preserve these default-“0” functions:

- projection.project.
- storage.safe_append_event, evaluate_whole_view, read_belief and
  read_projection_status.
- skeleton._record, record_observation and record_correction.

The legacy parser allowlist is src/nyx/cli.py::_parser (`--projector`),
scripts/seed_store.py::main (`--projector`), and
scripts/verify_store.py::main (`--projector`): each retains literal default "0".
The explicitly legacy scripts/seed_store.py::seed_store(..., projector="0")
and scripts/verify_store.py::verify_store(..., projector="0") boundaries also
remain unchanged. They are not changed to “2” or made implicitly stage two.

The existing default-“1” materialize_pending and read_belief_status become
explicit even though they can serve “0” when it is supplied; explicit “0” behavior
is unchanged. This is omission refusal, not removal of legacy support.

No Layer A event, schema, lineage commitment, candidate standing, cutoff,
freshness, publication or recovery algorithm changes. This decision does not
authorize merge/split/correction handlers, the sole-writer model, vocabulary
enforcement, or Step 2. New probe_store_scaling.sample already requires its
version; the whole-store probe explicitly compares both versions and does not
supply a missing stage-two function argument.

## Narrow ADR 0025 amendment

In ADR 0025 section 1, this acceptance replaces only:

> Existing API defaults remain unchanged.

with:

> Existing API defaults remain unchanged, except that no selectable stage-two
> projector default may exist in src/ or scripts/ outside ADR 0032's explicit
> allowlist of legacy "0" entry points; stage-two selection is required and omission
> refuses without a replacement default.

The invariant includes diagnostic selection and private version aliases.
The following sentence, “Selection of "2" is explicit, never an upgrade or
fallback,” and all other section-1 guarantees remain unchanged. ADR 0025's
Status includes the explicit partial-supersession notice.

No other accepted ADR or specification requires amendment for this decision.
README's default descriptions, call examples and decision-to-code map, and
GAPS E2 status are reconciled with implementation; they are not authority amendments.

## Ratification

Accepted by the maintainer on 2026-09-23 with the invariant, commit-scoped
inventory and AST regression guard above. Authority edits and implementation
land separately: the maintainer commits the staged authority change, then
confirms it before the implementation change proceeds. The agent commits only
implementation files, never authority files, and never bypasses a commit hook.

For both ADR 0032 and ADR 0030, an implementation (B) change never edits
decisions/. After each (B) commit, the agent stages a separate one-line authority
(A) change marking that ADR's Implementation complete and citing the (B) commit
hash, then stops for the maintainer to commit it. The completion marker is never
included in the implementation commit.

## Acceptance cases

- Walk src/ and scripts/ ASTs and reject all non-allowlisted version parameter
  defaults, including future/private functions and constant-valued defaults.
- Check scripts/probe_lineage_scaling.py's argparse --projector-version option:
  it must be required and have no default; omission refuses before probe work.
- Inventory all selectable defaults, including the constant-valued constructor,
  private version alias and diagnostic parser. Each enumerated omission refuses.
- Verify omission before observable work or mutation, covering preparation,
  submit, skeleton writers, reads, publication, recovery and snapshot construction.
- Update callers and the test-local submit wrapper with explicit versions.
  Prove there is no hidden replacement default in a wrapper or diagnostic.
- Explicit “1” and “2” retain existing supported behavior and frozen fixtures;
  unsupported versions refuse without fallback. Supported explicit “0” calls
  through shared helpers remain valid.
- Legacy default-“0” APIs and the CLI retain their current omission behavior.
- Run full tests on Python 3.14 and check_docs before an implementation commit.
  The scaling evidence motivates selection visibility, not a new latency gate.
