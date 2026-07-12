# Nyx Council Protocol

**Purpose:** who reviews what, and two failure modes caught tonight worth guarding against going forward. Not architecture, not implementation — process.

---

## Roster (evidence-based, not vibes)

Specialization below is what actually happened across tonight's review passes, not an assumed ranking. Re-check it periodically against new evidence rather than treating it as fixed.

- **GPT** — abstraction, systems architecture, spotting common primitives. Landed the oracle-class split, the support-set concept, the organs-as-control-plane-primitives mapping.
- **Claude** — constitutional consistency, contradiction detection, invariant enforcement. Caught the identity/determinism scoping conflict, pushed back on affective invariance overreach, flagged where a "helpful" addition would have quietly violated an existing invariant.
- **Qwen 3.7 Plus** — implementation correctness, deterministic systems behavior, storage/database mechanics. Caught JSON canonicalization non-determinism, hash-chain fold-ordering non-determinism, the missing stale-read index — three bugs that would have caused silent corruption, missed by every other reviewer including architecture-focused passes. Also self-retracted a fabricated number without being asked.
- **GLM** — adjacent applications, creative extensions, overlooked reuse opportunities. Produced the strongest "exploits" document (PII detection reuse, capability-registry auto-calibration) but needs its output checked against §10's closed list — one exploit (context compaction) would have quietly bypassed epistemic safeguards if taken as written.

## Routing rule

- **Architecture / design questions** ("is this the right abstraction," "does this violate an invariant," "is this creep") → GPT + Claude, cross-checked against each other.
- **Implementation-shaped questions** ("will this literal function work," "is this deterministic," "does this schema hold under concurrent writes") → **Qwen first.** This is the newly-earned lane as of tonight.
- **"What else can we build with what we have"** → GLM, but treat output as proposals, not decisions — check every "exploit" against §10 before folding in.
- **Multi-model hand-off compilation** → whoever's available compiles; see hygiene rule below before trusting the result.

## Process hygiene (two failures caught tonight)

**1. A model can review a stale cached version and not know it.** Grok gave near-identical feedback across three passes on materially different document versions — including flagging things that were already fixed. It wasn't re-reading, it was pattern-matching to a remembered critique. **Fix:** before trusting a review, ask the reviewer to quote something specific from the *current* text. If it can't, the review is worthless regardless of how confident it sounds.

**2. A hand-off compiler can smooth its own reframing into the same tone as consensus.** GPT's hand-off stated "Nyx is an epistemic kernel implemented as a deterministic governance kernel" as if settled — it wasn't; it was one contributor's elegant-sounding scope expansion that quietly contradicted §10's closed design filter. It read as agreed because compiled summaries default to one confident voice. **Fix:** whoever compiles a hand-off tags their own interpretive additions separately from what the sources actually agreed on. Don't let the compiler role become the least-checked voice in the council just because it writes last.

**3. The entire council reviews; nobody executes — this is the biggest blind spot.** Every model does static analysis of the artifact. After eleven passes, the surviving bugs were *all* composition or seam failures (out-of-order fold at the reconnection seam, stale-read race, two files silently disagreeing about the same table) — never component failures, because reviewing "is this component right" cannot catch "do these components compose." No additional model fixes this; it is methodological, not a roster gap. **Fix:** before trusting a hardened spec, run worked traces through the seams by hand or by the walking skeleton — minimally one hostile-input trace and one reconnection trace (V0 §5). Review catches component bugs; only execution catches seam bugs. Treat "has this been *run*, not just *read*" as a distinct and higher bar.

**4. "Simulate" beats "list concerns" — the active ingredient is forward-tracing, not model choice.** Asking Fable to forward-simulate the write path (event arrives, envelope hashed, payload encrypted, index updated, fold, sweep, gate) surfaced the dual-root crash gap and the correlated-corroboration bug — both only findable by walking steps in sequence, invisible to a severity-ranked listing. A plain "3 concerns / 3 improvements" prompt reliably pulls generic review-mode output (bus factor, scope creep, test coverage) instead. **The template, reusable with any model:** *"Simulate [system] forward through [workflow]. Report where the spec goes silent and you have to improvise. Rank by recurrence during the trace, not by how severe each gap sounds."* Recurrence-during-the-trace is a cheaper and more honest selection criterion than asking a model to introspect on its own "activations" — a model that can't actually instrument itself and plays along anyway hands back confabulated introspection dressed as data, which is worse than not asking. If introspection framing is used at all, require the model to flag it as unverifiable and show that the underlying argument holds independent of the introspective claim. Counterfactual claims about what a plain prompt *would* have produced are predictions, not measurements — testable cheaply (fresh sessions, same model, plain vs. trace prompt, diff the outputs) rather than taken on faith.

---

## Roster addendum
**Fable** — added lane: forward-simulation of a design through a live workflow, surfacing seam/composition bugs no static review catches. Distinct from Qwen's implementation-correctness lane (which catches mechanical bugs on read) and from GPT/Claude's architectural-consistency lane (which catches conceptual contradictions). Fable's value is specifically in *simulate*, not in any special reasoning capability — the prompt structure is the mechanism, and it transfers to other models per the template above.

---

*This file itself should get the same scrutiny — if the roster stops matching evidence, or a new failure mode shows up, update it rather than defer to what's written here.*
