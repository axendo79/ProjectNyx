"""Nyx — an epistemic kernel.

The protected core that governs what a system believes and how those beliefs are
earned. Layer A (append-only event log) is the epistemic ground record; the
Resolved View is a deterministic, materialized projection of it. See spec/.

SCAFFOLD STATUS: every callable in this package currently raises
NotImplementedError by design. Commit 1 is the known-good structural baseline
with no logic. Logic lands test-first in the walking skeleton (commit 2) —
spec/NYX_V0_IMPLEMENTATION.md §6.
"""

CONSTITUTION_VERSION = "v1.x"  # spec/NYX_ARCHITECTURE.md §Constitution
SCHEMA_VERSION = "0"          # bump on any spec/NYX_V0_IMPLEMENTATION.md §4 change
