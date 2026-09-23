"""Stage-two semantic preparation and sole-writer submission (ADR 0030).

Before commitment, retain the EventRequest / PayloadRequest pair, including IDs
and full source.config. Retry that same semantic request, without reminting.
The writer assigns recorded_at and the predecessor under the append lock.
After commitment, submit returns the original committed Envelope / Payload pair;
retain it as the result. Retrying the semantic request returns that same pair.
No implicit mention creation or resolver lookup.
"""

from . import storage, writer
from .events import ENTITY_MENTION_RECORDED, OBSERVATION_RECORDED, ORIGIN_OBSERVED
from .timestamps import validate_timestamp


def prepare_mention(conn, *, mention_id, subject_id, text, source, source_class,
                    occurred_at, origin_type, event_id=None):
    validate_timestamp(occurred_at)
    return writer.prepare_event(
        event_type=ENTITY_MENTION_RECORDED, origin_type=origin_type, source=source,
        source_class=source_class, occurred_at=occurred_at,
        payload={"mention_id": mention_id, "subject_id": subject_id,
                 "text": text, "link_state": "constitutive"},
        entity_refs=[subject_id], event_id=event_id)


def prepare_observation(conn, *, claims, source, source_class, occurred_at,
                        event_id=None, projector_version):
    """Name the current belief; the caller supplies fresh IDs for new containers.

Every claim supplies a fresh claim_candidate_id, mention_id, subject_id,
property_id, value and verifiability. A supplied conflicting belief_id refuses;
the writer never redirects a submitted association.
    """
    validate_timestamp(occurred_at)
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
    return writer.prepare_event(
        event_type=OBSERVATION_RECORDED, origin_type=ORIGIN_OBSERVED, source=source,
        source_class=source_class, occurred_at=occurred_at, payload={"claims": recorded},
        entity_refs=sorted({c["subject_id"] for c in recorded}),
        event_id=event_id)


def submit(conn, recorded_event, as_of, projector_version):
    """Submit retained semantics; return the original committed pair on retry.

    Before commit only positions may change. Append and derived publication are
    separate transactions; a publication failure never uncommits Layer A.
    """
    writer.validate_request(recorded_event)
    storage._registered_projector(projector_version)
    with conn.append_lock:
        storage.materialize_pending(conn, as_of, projector_version)
        committed = storage.append_submission(conn, recorded_event, projector_version)
        storage.materialize_pending(conn, as_of, projector_version)
        return committed
