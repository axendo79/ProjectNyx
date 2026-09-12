"""Stage-two writer preparation. Retain the returned event for every retry.

Preparation is not append: the caller retains IDs and the complete Envelope /
Payload pair before submitting. No implicit mention creation or resolver lookup.
"""

from . import storage
from .events import ENTITY_MENTION_RECORDED, OBSERVATION_RECORDED, ORIGIN_OBSERVED, build_event


def prepare_mention(conn, *, mention_id, subject_id, text, source, source_class,
                    occurred_at, origin_type, event_id=None, recorded_at=None):
    return build_event(
        event_type=ENTITY_MENTION_RECORDED, origin_type=origin_type, source=source,
        source_class=source_class, occurred_at=occurred_at,
        payload={"mention_id": mention_id, "subject_id": subject_id,
                 "text": text, "link_state": "constitutive"},
        prev_event_hash=storage.last_event_hash(conn), entity_refs=[subject_id],
        event_id=event_id, recorded_at=recorded_at)


def prepare_observation(conn, *, claims, source, source_class, occurred_at,
                        event_id=None, recorded_at=None, projector_version="1"):
    """Name the current belief; the caller supplies fresh IDs for new containers.

Every claim supplies a fresh claim_candidate_id, mention_id, subject_id,
property_id, value and verifiability. A supplied conflicting belief_id refuses;
the writer never redirects a submitted association.
    """
    recorded = []
    for claim in claims:
        claim = dict(claim)
        current = storage.lookup_current_belief_id(conn, claim["subject_id"], claim["property_id"], projector_version)
        if current is not None:
            if "belief_id" in claim and claim["belief_id"] != current:
                raise ValueError("submitted belief_id differs from current belief")
            claim["belief_id"] = current
        elif "belief_id" not in claim:
            raise ValueError("new belief requires a retained recorded belief_id")
        recorded.append(claim)
    return build_event(
        event_type=OBSERVATION_RECORDED, origin_type=ORIGIN_OBSERVED, source=source,
        source_class=source_class, occurred_at=occurred_at, payload={"claims": recorded},
        prev_event_hash=storage.last_event_hash(conn),
        entity_refs=sorted({c["subject_id"] for c in recorded}),
        event_id=event_id, recorded_at=recorded_at)


def submit(conn, recorded_event, as_of, projector_version="1"):
    """Append the exact retained pair, then separately publish pending records."""
    storage.materialize_pending(conn, as_of, projector_version)
    appended = storage.safe_append_event(conn, *recorded_event, projector_version)
    storage.materialize_pending(conn, as_of, projector_version)
    return appended
