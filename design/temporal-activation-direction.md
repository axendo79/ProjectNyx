# Temporal and activation direction

**Status:** Unratified design direction. Does not authorize implementation, supply missing defaults, or supersede accepted decisions.

**Provenance:** Originated in conversation, recorded 2026-09-07. This document preserves the user's design direction and the subsequent feedback-loop review; it is not a ratified specification. Recommendations and candidate definitions below remain proposals.

## Temporal layer

Machine-readable temporal information: `event_time`, `first_seen`, `last_referenced`, `last_activated`, `sequence_id`, and `relations`. Relative dates are derived from timestamps rather than stored as authoritative relative descriptions.

These field names express the direction, not an approved schema. Their meanings, scope, sources, and relationship to existing timestamps remain subject to the decisions below.

## Activation surface

Activation is ephemeral, deterministic, logged, and replayable. It cannot create facts, mutate Layer A, or self-promote. It biases retrieval, never filters.

Proposed components:

- Recency.
- Frequency.
- Context/goal bias.
- Refractory suppression.
- Decay.

Novelty and temporal-contradiction salience are proposed activation injections. They are operational attention signals, not evidence or truth judgments. Their detectors, baselines, inputs, and replay behavior require decisions.

Retrieval coherence is proposed observability for `/audit` and `/selftest`. Neither interface exists in this repo as of this recording; both are proposed interfaces, not extensions to implemented commands.

Soar's separation of long-term semantic/episodic memory from working memory was cited in conversation as precedent. It motivates a separation of responsibilities, not adoption of Soar's complete architecture or proof that Nyx's proposed activation policy works. References: [semantic memory](https://soar.eecs.umich.edu/tutorials/soar_tutorial/07/) and [episodic memory](https://soar.eecs.umich.edu/tutorials/soar_tutorial/08/).

## Deferred as experimental

- Spreading activation.
- Activation budget.
- Nonlinear interference.
- Multi-timescale decay.

These are experiments deferred pending baseline behavior and measurements, not approved implementation work or missing defaults to invent.

## Explicit non-goals

- Hemispheric architecture.
- Consciousness/emotion/self-model.
- Wave simulation.

These exclusions are distinct from the deferred experiments. Their intersection with existing affect and personality-emergence material is unresolved below.

## Decisions needed before code

| Area | What needs settling |
|---|---|
| `event_time` | Whether this is an alias for existing `occurred_at`, or a distinct concept. Do not introduce a second timestamp with overlapping meaning. |
| `first_seen` | First seen by which subsystem, for which identity? A candidate is earliest qualifying `recorded_at`, but merges, duplicates, and historical cutoffs need definitions. |
| `last_referenced`, `last_activated` | Precisely which operations count, where those operations are recorded, and how replay reconstructs them. They describe usage, not world truth. |
| `sequence_id` | Relationship to the existing insertion-order replay contract; stability across export, restore, and replay. |
| `relations` | Typed, provenance-backed relations versus operational associations. Proposed associations must not become accepted facts implicitly. |
| Relative dates | Explicit reference time and timezone, including historical replay. “Yesterday” must not depend on the replay machine’s current clock. |

The accepted [projection-parameters ADR](../decisions/0010-projection-parameters.md) supplies inclusive `recorded_at` cutoffs, explicit evaluation time, and version dispatch. It does not settle these temporal definitions or specify activation. The separate [Python-target ADR](../decisions/0009-python-314-re-adopted-as-target.md) retains number 0009; the projection-parameters ADR is now 0010 (formerly 0009).

## Retrieval feedback loop

The conversation proposed that retrieval counts as a reference because excluding it would misrepresent what happened. Retrieval can then increase activation, which increases the chance of later retrieval. Three proposed mitigations were refractory suppression, separating retrieval from stronger reference signals, and logarithmic or capped frequency.

Assessment: these are useful mitigations, but insufficient to establish that the loop is controlled. They limit parts of the reinforcement mechanism; none yet guarantees exposure of relevant, previously unseen material through top-k.

### Observable event vocabulary

| Event | Meaning |
|---|---|
| Candidate generated | Item entered the retrieval candidate pool. |
| Selected/exposed | Item crossed top-k and was supplied to the consumer. |
| Referenced | Item was explicitly cited or linked to an action or output. |

“Retrieval counts as a reference” and “only material that informed something counts as a reference” are different definitions. Preserve what happened through explicit events, then decide which events influence activation.

“Actually informed something” is generally not directly observable. Injection establishes exposure; citation establishes an explicit reference. Neither proves causal influence. If `last_referenced` includes retrieval by definition, keep that meaning and give the stronger signal another name. Field names should not conceal the distinction. This vocabulary is proposed; it does not silently ratify the field definitions.

### Assessment of the proposed mitigations

1. **Refractory suppression can damp immediate repetition.** It bounds the loop only if its strength, duration, and update rules actually overcome reinforcement. A weak penalty may merely slow the same winner down. A session reset can erase suppression while preserving accumulated frequency, allowing the loop to resume. Suppression can also penalize a repeatedly useful source during a sustained task.

2. **Splitting exposure from use is the strongest structural improvement.** Candidate generation should not, by itself, earn the same reinforcement as an explicit reference. Otherwise larger candidate pools manufacture more “usage.” However, the stronger signal remains downstream of retrieval: items must usually be exposed before they can be cited. Citations can therefore reinforce an exposure advantage. Treating injection as a strong signal makes this especially circular, because the retrieval system itself chooses injection.

3. **Logarithms and ceilings limit score growth, not necessarily dominance.** A logarithm remains unbounded. A ceiling bounds frequency's contribution, but a saturated item can still permanently beat competitors if that contribution outweighs relevance differences. The relevant bound is frequency's influence relative to the other ranking terms.

### What is still missing

- **Update timing and deduplication.** Proposed rule: rank from a fixed pre-request state, then record outcomes. Decide whether repeated tool calls, retries, pagination, and multiple citations count once or many times. Otherwise orchestration details manufacture reinforcement.
- **Scope.** Global frequency can carry yesterday's popular topic into today's unrelated task. Define whether counts and refractory effects are global, per goal, per session, or some combination.
- **Credit assignment.** Specify whether reinforcement attaches to an event, chunk, belief, source, or entity. Duplicate chunks can crowd top-k; broad entity-level credit can boost unrelated claims.
- **Feedback across components.** One retrieval might update frequency, recency, and `last_activated` simultaneously. Capping frequency alone leaves the combined loop uncontrolled. Activation calculation should not recursively generate reinforcement merely because an item received a score.
- **Candidate-generation bias.** Eligibility does not ensure consideration. If activation also influences candidate generation, items can disappear before ranking. Even with fixed candidates, top-k can make suppression effectively indistinguishable from exclusion to the consumer.
- **A route for underexposed evidence.** The three mitigations provide no exposure guarantee. If starvation appears, consider an independently generated relevance candidate pool or a measured exposure mechanism. Either needs its own design decision, not an implicit activation budget.

Novelty and contradiction salience might challenge incumbents, but only if their detectors can examine material outside the favored top-k. Otherwise they inherit the same blind spot.

“Biases retrieval, never filters” needs an executable definition: activation would change ordering within the otherwise eligible candidate set, refractory suppression would lower priority without changing eligibility, and activation would leave belief state, evidence, confidence, and Layer A unchanged. Pagination/top-k must expose the practical consequences of reordering: an eligible item can still disappear from the first page. These are proposed acceptance properties, not a settled retrieval contract.

### Measurements and evaluation

Use a baseline with activation disabled, test each mitigation separately, then combinations.

| Measure | What it answers |
|---|---|
| Relevant-evidence recall@k, including opposing evidence | Does activation improve access to useful evidence or bury it? |
| Exposure concentration and time to first exposure | Do a few items dominate while relevant alternatives remain unseen? |
| Quality after a goal/topic switch | Does historical popularity overpower current relevance? |
| Recovery after fresh contradictory evidence arrives | Can new evidence displace a reinforced incumbent? |
| Ranking changes after one artificial extra exposure | How strongly does a small accidental advantage amplify? |
| Repetition versus task success | Is suppression reducing redundancy or withholding repeatedly necessary evidence? |
| Per-component score contributions | Which terms actually cause top-k crossings? |

The key experiment is closed-loop evaluation. Replaying fixed recorded reference events tests determinism, but not feedback: a different ranking would have produced different exposures and subsequent references. Run paired trajectories from identical starting states where each policy receives its own resulting feedback. Begin with controlled tasks and explicit relevance judgments; then validate against real usage.

Include repeated queries, retries, session resets, abrupt topic changes, duplicate material, and late-arriving counterevidence. Track exposure and reference counts separately throughout.

The review recommends signal separation and explicit update rules as prerequisites, then testing refractory suppression and bounded frequency as hypotheses. Define acceptable relevance loss, repetition, starvation, and recovery time before tuning. No numerical thresholds or coefficients are settled here. Bounded scores and deterministic replay are necessary engineering properties; they do not establish healthy retrieval behavior.

## Conflicts and unresolved boundaries with accepted specifications

### Durable activation inputs versus Invariant 8

[NYX_ARCHITECTURE.md](../spec/NYX_ARCHITECTURE.md), Invariant 8, makes a Layer A append the only durable commit and requires reconstructible derivatives. Ephemeral activation state cannot be replayed from lost reference/exposure history. Retained operational inputs outside Layer A are a proposed solution, but they create an explicit authority tension that must be resolved, not assumed away.

The architecture's separate, crash-durable, mutable process traces (§7) and outside-the-truth-ledger parameter-change events (§4) provide related precedents. Neither automatically authorizes an activation log. An accepted decision must specify the operational log's authority, retention, ordering, configuration versions, recovery, and replay scope. “Ephemeral” can describe derived state while inputs persist, but that distinction is not yet ratified. Activation must not write its own salience back as world evidence.

### Affect and personality-emergence intersection

The explicit non-goal of a consciousness/emotion/self-model intersects existing affect and personality-emergence material. Architecture Invariant 11 specifies affect handling, self-reference tagging, and a ceiling; §13 includes an unspecified personality-emergence layer. Ratification must clarify whether the new exclusion removes any existing direction or only excludes a consciousness/emotion/self-model subsystem. Presentation-level affect handling and such a subsystem are not automatically equivalent.

Context/goal bias must not silently import affect into ranking or epistemic authority. Existing affect restrictions remain authoritative until explicitly reconciled. This document neither deletes those requirements nor approves the broader emergence layer.

### Scope, temporal semantics, and implementation authority

Architecture §10 closes the kernel's governance scope. The placement of activation as a read-side retrieval facility needs an explicit decision; this document does not expand that scope.

Existing `occurred_at`, `recorded_at`, insertion-order replay, and the projection-parameters ADR remain authoritative. New names do not authorize schema changes or a historical-validity interpretation that contradicts the knowledge-time cutoff. Backdated-correction semantics remain open under [ADR 0005](../decisions/0005-backdated-corrections-fail-loud-pending-semantics.md).

Operational associations do not authorize identity merges or cross-belief projection behavior. [ADR 0008](../decisions/0008-fold-signature-cannot-express-cross-belief-events.md) remains the fold-shape/hash-lineage blocker; missing global event dispatch is a separate existing gap. Additional origin-state semantics also remain undecided.

The proposed `/audit` and `/selftest` interfaces and retrieval-coherence measures have no existing implementation contract. Their names do not imply that command handlers or approved metric definitions already exist.

## Proposed sequencing against existing gaps

1. Preserve this direction and its non-authoritative status; ratify concrete contracts before dependent implementation.
2. Address the existing ingestion timestamp-canonicalization and database-version-check gaps before persistent temporal data. Require migrations when persistent data needs conversion.
3. Ratify temporal meanings, then build the smallest read-side temporal surface using existing projection behavior where appropriate. Preserve fail-loud behavior for unsettled corrections and origins.
4. Establish baseline retrieval and observable relevance outcomes before ranking bias. Specify proposed audit/selftest interfaces and address the existing stale-read detection stub as part of the read path.
5. Ratify activation's storage, authority, replay, update, and ranking contracts. Implement and evaluate only the minimal components after those decisions, with versioned operational defaults and explicit retuning criteria.
6. Keep cross-belief work behind ADR 0008 and relevant dispatch decisions. Fix redaction replay before supporting redacted histories, including activation logs or caches that could retain payload-derived content. Defer experimental mechanisms until baseline measurements justify them.

A read-only ranking experiment over existing beliefs need not resolve every open gap, but it cannot bypass a gap by implementing undecided semantics. New feature questions belong here until ratified; [GAPS.md](../GAPS.md) remains the register of verified existing findings, not a general wishlist.
