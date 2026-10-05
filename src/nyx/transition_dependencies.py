"""ADR 0035 section 2's closed, read-only recorded dependency check.

Transition handlers must call this on the locked pre-event snapshot at append
and replay. Eligibility and live-status checks belong to those handlers. No
transition handler is registered yet; the committed schema boundary is STUCK.
"""
from .reducer import _required


def check_transition_dependencies(snapshot, targets):
    """Refuse undecided dependent demotion/restoration under ADR 0015 section 5."""
    target_ids = set(targets)
    for identifier in targets:
        candidate = _required(snapshot, "claim_candidates", identifier)
        if (candidate["verification_basis"]["kind"] != "direct_observation"
                or candidate["predecessors"] or candidate["restrictions"]
                or candidate["opposing_events"]):
            raise NotImplementedError("transition dependency requires ADR 0015 section 5")
    for candidate in snapshot.records("claim_candidates").values():
        if any(identifier in candidate[field] for identifier in target_ids
               for field in ("predecessors", "restrictions")):
            raise NotImplementedError("transition dependency requires ADR 0015 section 5")
