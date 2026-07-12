"""Operational v0 defaults — SETTLED (spec/NYX_V0_IMPLEMENTATION.md §2, §7 case 1).

These are placeholders with STATED retune triggers, not truth formulas. Wrong
values cost performance/ordering, never epistemic integrity. Code against them
directly; do NOT silently "improve" them while implementing — if one looks wrong,
flag it in a decision-log entry rather than changing it (§7).

Nothing here is a Constitution amendment. Epistemic formulas stay deferred (§3);
only these operational knobs are set now.
"""

from __future__ import annotations

# Liver priority-queue score weights (spec/NYX_V0_IMPLEMENTATION.md §2).
# priority = w1*days_since_last_audit + w2*reference_count
#          + w3*is_single_source + w4*is_low_confidence_source
# v0: arbitrary roughly-equal starting point — establishes AN order before data.
# RETUNE WHEN: enough Liver history exists to see which flagged items led to a real
# demotion/correction vs. false alarms; reweight toward what predicted real problems.
LIVER_WEIGHTS = {"age": 1, "refs": 2, "single_source": 3, "low_conf_source": 3}

# idle_compute_budget (spec/NYX_V0_IMPLEMENTATION.md §2, architecture §6).
# RETUNE WHEN: running on real hardware (2080 Ti now, eventual 22GB card) — these
# are guesses about headroom, not measurements.
IDLE_MAX_VRAM_FRACTION = 0.15          # max 15% VRAM for background Dream/Liver while idle
IDLE_MAX_BACKGROUND_TOKENS_PER_MIN = 2000
IDLE_FOREGROUND_YIELD_MS = 750         # halt new background GPU submission within ~500ms–1s
                                       # of a foreground request (poll interval, not interrupt)

# Minimum sample floor — corroboration gate (spec/NYX_V0_IMPLEMENTATION.md §2).
# v0: 2 independent corroborating SOURCE CLASSES for unverified -> verified via
# corroboration. A direct world-oracle confirmation promotes on its own (Inv. 4),
# not subject to this count.
# RETUNE WHEN: you observe how often single-vs-double corroboration proved reliable.
MIN_CORROBORATION_SOURCES = 2

# Spleen alert thresholds (spec/NYX_V0_IMPLEMENTATION.md §2).
# RETUNE WHEN: a trailing "normal" baseline exists to be a multiple of.
CONTRADICTION_RATE_ALERT_MULTIPLE = 2.0   # fire if unresolved contradictions > 2x trailing 7-day avg
IMMUNE_FALSE_POSITIVE_HALT_FRACTION = 0.05  # halt retraining if FP rate > 5% of intake (rolling window)
