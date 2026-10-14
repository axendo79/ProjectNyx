# Preparation plan for Proposed ADRs 0036 and 0037

**Status: Non-authoritative implementation plan, not authorization.**

Prepared 2026-10-14 against `origin/main` at `70a4b97`. Proposed
[ADR 0036](../decisions/0036-strict-payload-keys.md) and Proposed
[ADR 0037](../decisions/0037-o3-mention-discovery.md) are unratified. Their
confirmed drafting answers do not permit implementation. The shared V1-V9
boundary is the single section in Proposed
[ADR 0036](../decisions/0036-strict-payload-keys.md#shared-version-boundary).
This plan closes no GAPS entry, changes no authority, and supplies no missing
semantic default or production API name.

The [strict-payload design record](2026-10-14-adr-draft-strict-payload-keys.md)
and [O3 design record](2026-10-14-adr-draft-o3-discovery.md) preserve drafting
history. The numbered proposals are the review records. Accepted ADRs still
govern shipped code, including ADRs 0030/0032 for writer ownership and selection,
0034/0035 for projector-3 transitions, 0024 for no head, and 0031 for public report
scope and specialized report-reader guards.

## Parked acceptance drafts

The local, ignored files are:

| Alias | Local path | Test functions | Planned parameter cases |
|---|---|---:|---:|
| SP | `scratch/pending-tests/test_adr0036_strict_payload_keys.py.pending` | 37 | 131 |
| O3 | `scratch/pending-tests/test_adr0037_o3_discovery.py.pending` | 44 | 523 |

The case counts expand literal parametrizations and O3's three-version `ready`
fixture; they are planning counts, not collected or passing-test claims. Each
test cites the relevant clauses. The `.pending` suffix follows the existing
`scratch/test_forward_verifier.py.pending` convention. Neither file is part of
the normal pytest suite or this commit; they must remain in this worktree for
local review. Scratch artifacts require separate retention if the worktree is
removed.

Current event/request types, append/publication/read calls, projection APIs,
transition helpers and frozen R092 report inputs are used directly. New APIs and
instrumentation have explicit TODO bindings. Binding names for unspecified
helpers and metadata nesting are test-adapter vocabulary, not decisions about
production names. Activation must replace these with thin real bindings; it may
not return fabricated success metrics or silently introduce defaults.

The drafts include an independent ordered-pair duplicate oracle, complete
snapshot membership/query enumeration, exact prospective O3 DDL assertions,
direct constraint violations, all-row rollback comparisons and allocator spies.
Verifier tests disable production reconstruction/query paths. Fault witnesses
must prove the targeted write occurred; process-death tests require an actual
killed child. Unsupported transition semantics are not manufactured merely to
exercise a table: relation-write tests select only "3"/"4". Supplied historical
lifecycle fixtures exercise index filters without implementing merge/split.

## Delivery gate and test-first procedure

Before any dependent implementation, the maintainer must explicitly ratify both
numbered proposals and their shared schema-6 layout, record the authority changes
under [AGENTS.md's ADR commit protocol](../AGENTS.md#adr-commit-protocol), commit
them, and confirm that commit. Agents never set `NYX_AUTHORITY_COMMIT`, commit
authority files, or bypass hooks. V9 is a delivery precondition; it proposes no
runtime authority-policy subsystem.

After that confirmation, review these drafts against the actual Accepted clauses.
For each bounded slice, bind and temporarily exercise its named tests, demonstrate
the intended failing assertion, implement only the accepted behavior, and make
those tests pass. Move completed tests into normal collection only when the
required behavior exists. Leave later cases parked; no skip/xfail or knowingly
failing normal-suite test is a delivery shortcut. Run the full `pytest -q` suite
and doc checker before each implementation commit. Future commits stay scoped
to one ADR in dependency order, with authority and implementation separate and
maintainer completion markers separate. The slice list is a dependency plan,
not permission to combine ADR implementation commits or relax that protocol.

Every slice below is conditional on joint ratification. In the test column,
`SP:` and `O3:` select the corresponding parked file and names are exact pytest
functions. An integrated test becomes fully green only when all its listed
dependencies are implemented; an early slice must not claim the entire test
passes merely because one assertion now passes.

## Ordered slices

| Slice and dependency | Bounded work after acceptance | Pending tests completed by this slice/dependency chain | Main risk |
|---|---|---|---|
| 01. Joint authority receipts and selectors | Bind V9's maintainer-confirmation evidence; inventory new explicit selectors and preserve the ADR 0032 allowlist. | SP: `test_v9_activation_has_joint_maintainer_authority_receipts`, `test_v1_identifiers_and_selector_signatures`, `test_t3_selector_refuses_before_work`; O3: `test_a12_new_selector_guards_refuse_before_storage_work` | Mistaking identifier/drafting confirmation for ratification, or hiding selection in a wrapper. |
| 02. Schema-6 final layout | Fresh creation/validation admits the one joint layout. Amend exactly the two committed constraints and add all O8 tables/indexes together. No temporary alternate layout called 6. | O3: `test_a10_exact_schema6_tables_and_access_indexes`, `test_a10_schema_constraints_reject_invalid_rows`; SP: `test_v1_identifiers_and_selector_signatures` | Widening Layer A DDL, unrelated constraints, or genesis progress while changing compatibility. |
| 03. Frozen schema opens | Preserve supported schema-4/5 opens, outputs and refusal behavior; expose O3 migration-required unavailability and strict-4 refusal without mutation. | SP: `test_t8_old_schema_refuses_strict_without_implicit_migration`; O3: `test_a10_old_schema_queries_are_unavailable_without_open_time_migration` | Implicit table installation or migration during open/query. |
| 04. Narrow working-copy migration | Validate distinct exact copies; apply accepted 4-to-5 and proposed 5-to-6 changes in one migration transaction. Verify every old row and unrelated DDL. Keep migration separate from backfill. | SP: `test_t8_migrate_distinct_copy_preserves_source_rows_and_unrelated_ddl`, `test_t8_migration_rolls_back_every_write_group`; O3: `test_a10_migration_and_backfill_have_separate_atomic_failure_states` (migration branch) | Altering the only original, losing old committed rows, or leaving partially migrated metadata. |
| 05. Raw duplicate predicate and error | Parse ordered members recursively before mapping conversion; exact decoded-key equality, traversal order and object-path errors. Keep strings inert and syntax errors distinct. | SP: `test_t1_recursive_decoded_duplicate_predicate`, `test_t1_unique_controls_strings_are_inert`, `test_t1_t3_syntax_is_distinct` | Bottom-up parser traversal reporting a later duplicate, raw-escape comparison, or accidental Unicode normalization. |
| 06. Append profile/backstop | Distinguish recorded envelope schema from projector/index/database versions. Validate exact strict text at ordinary and retained-pair boundaries, including locked substitution recheck. New "4" admission records "1". | SP: `test_t3_new_admission_profile_matrix`, `test_t3_strict_profile_never_reaches_frozen_payload_decoder`, `test_t3_locked_recheck_detects_ciphertext_substitution`, `test_t6_unique_keys_waive_no_existing_admission_check`; `test_t2_duplicate_refusal_at_each_outer_boundary` (append routes) | Canonicalizing away duplicates before checking or treating old-schema relabeling as retry repair. |
| 07. Preparation and submit order | Validate original raw input before open/allocation/retention and before flushing pending work. Mapping preparation checks its own final serialization before allocation. Keep multi-claim refusal atomic. | SP: `test_t2_raw_preparation_does_not_create_store_lock_or_manifest`, `test_t2_mapping_checks_serialized_text_before_its_id_allocation`, `test_t2_multiclaim_refusal_is_all_or_nothing`, `test_t2_duplicate_refusal_at_each_outer_boundary` (prepare/submit routes); O3: `test_a11_strict_duplicate_never_allocates_or_flushes_pending` | A wrapper creating a lockfile/manifest or publishing unrelated work before refusal. |
| 08. Retrieval and semantic collision rules | Verify stored pairs by recorded profile; compare all ADR 0030 caller-owned fields. Exact committed retrieval precedes target/readiness checks and performs no publication. Support S5's exact old retrieval under "4" without admitting new old events. | SP: `test_t4_old_duplicate_history_and_exact_retry_are_frozen`, `test_t4_projector4_retrieves_exact_committed_old_pair_without_publication`, `test_t4_semantic_collision_changes_refuse`, `test_t4_transition_retry_precedes_target_eligibility` | Equal canonical/idempotency hashes concealing changed text, schema or config; duplicate evidence after an uncertain acknowledgment. |
| 09. Raw-aware projector-4 fold | Add the raw-log adapter; dispatch each recorded profile before decoded reduction. Preserve projector-3 claim semantics with the separate lineage tag. Frozen decoded-log signatures remain frozen. | SP: `test_t5_projector4_requires_raw_input_and_checks_bad_suffix`, `test_t5_frozen_full_log_refuses_strict_suffix_even_before_cutoff`, `test_t5_mixed_profile_replay_preserves_history_and_tied_positions` | Decoded-only input being accepted as proof of strict origin, or integrity checks occurring after cutoff filtering. |
| 10. Complete fold and adoption proof | Compare every supported old prefix at shared evaluation time; allow only V2's enumerated lineage/version derivatives. Validate each version's own lineage; refuse unsupported source history. Retain unique noncanonical strict spelling and existing value/time domains. | SP: `test_v2_every_old_prefix_complete_semantics_and_own_lineage`, `test_t6_noncanonical_unique_text_is_retained_and_canonically_committed`, `test_t6_base_admitted_values_and_timestamp_spellings_are_not_new_domains`, `test_t8_unsupported_source_fails_prefix_proof_without_conversion`; O3: `test_a6_every_prefix_incremental_replay_index_and_queries` (projection assertions) | Removing arbitrary provenance fields to force equivalence, changing canonical hashes, or inventing a legacy conversion. |
| 11. Complete index membership | Build subject membership, mentions/text/joins and belief/property/lifecycle associations from the complete selected snapshot. Include mention-only subjects and exact UTF-8 BLOB keys. Property enumeration is distinct before pagination. | O3: `test_a1_a2_text_to_typed_traversal_preserves_every_candidate`, `test_a2_same_spelling_across_all_id_kinds_never_cross_resolves`, `test_a8_recorded_lifecycle_filter_does_not_invent_merge_handlers`, `test_a6_every_prefix_incremental_replay_index_and_queries` (membership assertions) | Using incomplete `projected_mentions`, joining only through beliefs, multiplying mention hits or coalescing by value/text. |
| 12. Ready genesis and availability | Validate table/format/version/anchor/key/join/lifecycle associations; represent ready empty as 0/null/null with no derived-progress row. Keep unavailable, valid empty and unknown scope distinct. | O3: `test_a7_ready_genesis_and_unbuilt_are_distinct`, `test_a7_detected_readiness_row_and_join_corruption_is_unavailable`, `test_a3_scope_absence_mention_only_and_zero_match_are_distinct` | Treating absent readiness as ready genesis or claiming a marker proves completeness. |
| 13. Explicit enrollment/reconciliation | Require caller-retained `indexed_projectors`, including empty. Separate explicit build/reconcile/disable from ordinary opening. Readiness loss blocks enrolled new work, while exact retrieval remains possible. Disable only the selected index rows/readiness. | SP: `test_t9_strict_admission_independent_of_optional_index`, `test_v3_explicit_configuration_and_reconciliation_survive_readiness_loss`; O3: `test_v3_explicit_enable_disable_reconcile_and_restart_configuration` | Inferring configuration from missing rows, silently disabling an obligation, or making strict admission depend on an optional index. |
| 14. Joint publication transaction | Keep append/freshness in the earlier transaction. For enrolled versions publish projection headers/nodes/roots/relations, changed O3 rows, readiness and progress atomically. Select a supported fixture that actually writes each fault target. | SP: `test_t9_joint_publication_rollback_and_selected_recovery`; O3: `test_a11_joint_publication_failure_never_advances_progress_ahead`, `test_a11_relation_publication_failure_for_transition_capable_versions`, `test_a12_publication_updates_only_changed_o3_associations` | Progress/readiness ahead of rows; false fault coverage for tables a delta does not write. |
| 15. Full replay rebuild and version isolation | Reconstruct from genesis, ignoring damaged derived rows. Replace only the selected projection/index pair at one requested prefix, preserving other versions. Apply global mixed-profile unavailability for old O3 before continuation handling. | O3: `test_v4_v5_rebuild_and_index_version_isolation`, `test_v4_mixed_profile_old_o3_unavailable_before_cursor_restart`, `test_v4_projector2_can_serve_supported_prefix_before_old_transition_suffix`; SP: `test_t9_joint_publication_rollback_and_selected_recovery`; O3: `test_a10_migration_and_backfill_have_separate_atomic_failure_states` (backfill/rebuild branches) | Repair using the corrupt index as oracle, relabeling old rows, or treating an old transition suffix like a strict profile. |
| 16. Public typed query and detail traversal | Implement O2's five keyword-only operations and the new same-prefix detail adapter. Preserve all live/retained candidates and ending relations; keep specialized report readers/importers at their existing guards. | O3: `test_a1_a2_text_to_typed_traversal_preserves_every_candidate`, `test_a1_a2_frozen_public_report_paths_and_revision_meaning`, `test_a8_forward_candidate_sets_and_container_lifecycle_are_separate` | Discovery implying world truth/identity, selecting a head, dropping retained candidates or extending report producers to "4". |
| 17. Literal grammar, byte ranges and limits | Exact/prefix matching uses binary UTF-8 ranges and literal starts-with verification. Validate scope/filter/query types and actual integer 1..1000 sizes. Default 100; page count/end are local to the publication. | O3: `test_a3_literal_grammar_matches_independent_unicode_oracle`, `test_a3_invalid_grammar_is_typed_without_mutation`, `test_a3_unencodable_text_refuses_without_replacement`, `test_a3_page_size_never_clamps_or_coerces`, `test_a3_limits_default_end_and_count_are_page_local`, `test_a12_prefix_successor_is_byte_range_not_utf8_collation` | LIKE/collation/metacharacter semantics replacing literal matching, normalization, coerced booleans or hidden limit clamping. |
| 18. Total order and cursor codec | Listings use ID bytes; search uses text bytes then mention ID. Implement exact canonical O6 cursor structure, defaults, arity/types/hex, eligible last keys, genesis/prefix and complete query bindings. | O3: `test_a4_keyset_pages_equal_complete_order_with_ties`, `test_a4_cursor_binds_every_exact_query_field`, `test_a4_cursor_canonical_structure_and_eligible_last_key`, `test_a4_same_prefix_rebuild_and_identical_store_copy_continue` | Offset pagination, hidden SQL-plan order, duplicate token members, weak query binding or pathname identity. |
| 19. Global freshness and transaction coherence | Read items, joins, applied anchor, append tip and cursor check in one transaction. Continue at the same published prefix with new stale disclosure; restart on publication advance, including equal timestamps. Same-prefix details follow the handle. | O3: `test_a5_global_staleness_pending_match_and_publication_restart`, `test_a5_real_read_transaction_crosses_publication_coherently` | Freshness based only on hits, stale empty presented as absence at tip, or mixing before/after metadata and items. |
| 20. Explicit historical discovery | Implement raw replay discovery separately from live queries. Validate the full supplied log, apply inclusive cutoff, enumerate/query in memory, bind exact evaluation time/source and prefix in cursors, and publish nothing. | O3: `test_a6_historical_discovery_uses_full_raw_input_inclusive_cutoff`, `test_a6_history_cursors_bind_source_time_and_resolved_prefix`, `test_a6_corrupt_or_unknown_suffix_refuses_before_earlier_cutoff`, `test_a6_every_prefix_incremental_replay_index_and_queries`; SP: `test_t5_mixed_profile_replay_preserves_history_and_tied_positions` | Answering history from today's index, crossing live/replay tokens, or skipping bad suffix integrity because the cutoff is earlier. |
| 21. Standalone verifier and completeness | Independently inspect raw strict pairs, replay semantics/lineage/relations and enumerate every O8 field/key/join. Compare missing and extra rows even with self-consistent metadata/counts; disable production parser/reducer/builder/query paths during witnesses. | SP: `test_t5_forged_strict_duplicates_fail_all_raw_boundaries`, `test_t10_independent_verifier_survives_disabled_production_paths`; O3: `test_a7_independent_exhaustive_audit_detects_omission_and_extra_rows`, `test_a6_every_prefix_incremental_replay_index_and_queries` (independent audit assertions) | Shared production bugs becoming their own oracle; inclusion proofs or digests mistaken for complete search. |
| 22. Optional read-only diagnostic | Separately expose deterministic duplicate findings and distinct syntax/unavailable failures. Enforce read-only access; do not gate adoption, modify state or append an audit/usage record. | SP: `test_t7_optional_diagnostic_is_deterministic_readonly_and_never_gates`, `test_t7_diagnostic_failures_are_not_clean_scans` | Treating historical duplicates as newly invalid old events or making a diagnostic a rollout prerequisite. |
| 23. Read-only copies, backup and restore | Enforce read-only query connections; forbid repair/fetch/extraction/usage/cache writes. Inventory all O11 mention copies and existing managed report/request/vocabulary inputs. Restore into an isolated working copy and prove replay equivalence without modifying the bundle. | O3: `test_a9_queries_are_enforced_readonly_with_no_usage_or_repair`, `test_a9_unavailable_and_stale_reads_never_reconcile`, `test_a9_backup_restore_inventory_and_rebuild_equivalence` | Omitting text-bearing cursor/output/WAL copies, losing managed inputs or auto-enrolling from query code. |
| 24. Actual crash/acknowledgment recovery | Kill a child before/after append commit, during each derived write group/rebuild and after publication before acknowledgment. Resume with retained exact requests; compare whole recovered records/indexes independently. | SP: `test_t9_actual_process_death_preserves_atomic_prefixes`; O3: `test_a11_actual_process_crash_and_retried_original_pair` | Exception-only tests hiding process durability defects, duplicate append after lost acknowledgment or partially ready indexes. |
| 25. Work counters and frozen boundaries | Trace O8 access paths on growing unrelated/matching corpora. Measure examined keys, bytes, cold/warm work and publication/rebuild costs without inventing a latency gate. Re-run frozen default/hash/root/report/domain refusals and all normal tests. | O3: `test_a12_indexed_query_access_and_honest_work_bounds`, `test_a12_publication_updates_only_changed_o3_associations`, `test_a12_frozen_bytes_report_and_unratified_scope_boundaries`; SP: `test_t10_scope_refusals_remain_unchanged` | Full snapshot/payload scans, rewriting unrelated associations, exaggerated constant-work claims, or importing private-codec/usage/merge authority. |

## Acceptance coverage and dependency limits

| Proposed acceptance family | Draft witnesses and delivery dependency |
|---|---|
| 0036 T1-T3 | Slices 05-07 establish predicate, independent boundaries, zero allocation/retention/publication and selector/locked backstops. Schema and owner configuration come from 01-04/13. |
| 0036 T4-T6 | Slices 08-10 preserve historical bytes/retries, raw corruption refusal, canonical commitments, mixed cutoffs, complete fold/replay and own-version lineage. Reads/publication/verifier corruption witnesses finish with 14-15/21. |
| 0036 T7 | Slice 22 is independently optional; earlier strict tests run without this diagnostic. |
| 0036 T8-T10 | Slices 03-04/10 cover adoption; 13-15/24 cover joint O3/crash behavior; 21/25 establish independence and frozen scope boundaries. Report histories also appear in O3's frozen public fixture and backup/restore witnesses. |
| 0037 A1-A4 | Slices 11-12/16-18 cover typed discovery, mention-only membership, report scope, Unicode/grammar/limits, total order and exact cursor binding. |
| 0037 A5-A8 | Slices 19-21 and 15-16 cover coherent global freshness, every-prefix/history equality, unavailable/corrupt/completeness outcomes and complete forward candidate sets. |
| 0037 A9-A12 | Slices 23-25, with 02-04/13-15, cover read-only copies, exact migration/rollback, actual death, strict/index boundaries, work counters and frozen APIs. |
| V1-V2 | 01-02/06/09-11/16/25: independent version axes, explicit selection, separately tagged "4", complete "3" equivalence on supported old prefixes, inherited refusals and frozen report guards. |
| V3-V4 | 07-08/13-15/19/24: validation before side effects, explicit retained enrollment configuration, separate append transaction, joint publication, version isolation, global tip and mixed-old O3 refusal. |
| V5 | 09-11/15/20-21: full raw integrity before cutoff, deterministic replay from genesis, complete independent rows and no hidden runtime/model/network/diagnostic inputs. |
| V6-V7 | 02-04/10/13/23: exact one-layout schema 6, original/copy preservation, narrow transactional migration, every-position proof, separately explicit backfill and inventory-preserving restore. |
| V8 | 06-08/12-15/19/21/23-24: all logical state preserved on refusal, no partially ready publication, globally stale older prefix, explicit recovery/disable and no read repair. |
| V9 | 01 and the delivery procedure: actual joint maintainer authority confirmation before activation; separate authority/implementation/marker commits. This preparation commit satisfies no implementation-completion requirement. |

Several API encodings remain implementation details even though their meanings
are proposed: duplicate-error subtype name, error-field adapter names, unspecified
page metadata nesting, strict raw-adapter/helper names and instrumentation seams.
Do not promote draft adapter choices into requirements. Conversely, O2 operation
names, O6 cursor fields/encodings, O8 DDL, version identifiers and declared error
meanings are explicit proposed clauses; changing them after acceptance requires
authority review, not an implementation guess.

Any conflict with the eventual Accepted text, unsupported source replay or newly
required unresolved semantics stops the dependent slice. This plan does not
resolve private numeric/resource decisions, redaction/erasure, report corrections,
stage-three authority, support attachment, merge/split or usage recording.
