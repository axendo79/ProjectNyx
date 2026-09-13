"""Nyx — an epistemic kernel.

The protected core that governs what a system believes and how those beliefs are
earned. Layer A (append-only event log) is the epistemic ground record; the
Resolved View is a deterministic, materialized projection of it. See spec/.

The legacy walking skeleton and stage-two projectors are implemented. Broader
subsystems and unresolved handlers remain stubs; README.md maps shipped behavior
to accepted decisions and executable tests.
"""

CONSTITUTION_VERSION = "v1.x"  # spec/NYX_ARCHITECTURE.md §Constitution
SCHEMA_VERSION = "0"          # event envelope version; distinct from DB schema version
