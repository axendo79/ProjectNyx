"""ADR 0030: writer ownership, semantic requests and bounded clock assignment.

Clock/threshold injection is a testing seam, not runtime configuration. Production
uses MAX_CLOCK_SKEW; changing that value requires an ADR amendment.
"""

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from threading import RLock

from . import SCHEMA_VERSION, hashing, integrity
from .events import Envelope, Payload
from .ids import new_event_id
from .timestamps import validate_timestamp

MAX_CLOCK_SKEW = timedelta(seconds=120)
POSITIONAL_DERIVED = frozenset({
    "recorded_at", "prev_event_hash", "event_hash", "payload_hash", "idempotency_key",
})


@dataclass(frozen=True)
class EventRequest:
    event_id: str
    schema_version: str
    event_type: str
    occurred_at: str
    source: str
    source_class: str
    origin_type: str
    entity_refs: str | None


@dataclass(frozen=True)
class PayloadRequest:
    event_id: str
    canonical_entity_id: str | None
    ciphertext: str | None
    redacted: bool = False


def semantic_contents(envelope, payload):
    """Compare the complement, so newly introduced fields cannot be ignored."""
    return tuple({f.name: getattr(record, f.name) for f in fields(record)
                  if f.name not in POSITIONAL_DERIVED}
                 for record in (envelope, payload))


def prepare_event(*, event_type, origin_type, source, source_class, occurred_at,
                  payload, entity_refs=None, event_id=None):
    """Retain semantic contents once; no clock sample or log position is needed."""
    validate_timestamp(occurred_at)
    event_id = new_event_id() if event_id is None else event_id
    return (EventRequest(event_id, SCHEMA_VERSION, event_type, occurred_at,
                         hashing.canonical_json(source), source_class, origin_type,
                         None if entity_refs is None else hashing.canonical_json(entity_refs)),
            PayloadRequest(event_id, None, hashing.canonical_json(payload)))


def validate_request(request):
    if (not isinstance(request, tuple) or len(request) != 2
            or not isinstance(request[0], EventRequest)
            or not isinstance(request[1], PayloadRequest)):
        raise ValueError("ordinary submission requires a retained EventRequest/PayloadRequest pair; "
                         "recorded_at and prev_event_hash belong to the writer")
    envelope, payload = request
    validate_timestamp(envelope.occurred_at)
    if envelope.event_id != payload.event_id:
        raise integrity.IntegrityError("envelope/payload identity mismatch")
    if payload.redacted or payload.ciphertext is None or payload.canonical_entity_id is not None:
        raise NotImplementedError("redaction or canonical key binding is not implemented")
    return json.loads(payload.ciphertext)


def assign(request, recorded_at, prev_event_hash):
    envelope, payload = request
    data = validate_request(request)
    material = asdict(envelope)
    digest = hashing._sha256_hex(hashing.canonical_json(data))
    material.update(recorded_at=recorded_at, payload_hash=digest,
                    idempotency_key=hashing.idempotency_key(
                        json.loads(envelope.source)["actor_id"], envelope.occurred_at, data))
    result = (Envelope(**material, prev_event_hash=prev_event_hash,
                       event_hash=hashing.event_hash(material, prev_event_hash)),
              Payload(payload_hash=digest, **asdict(payload)))
    integrity.decode_payload(*result)
    return result


def clock_now():
    return datetime.now(timezone.utc).isoformat()


class ClockSkewError(ValueError):
    """Synchronous refusal only; no durable alert state or recovery latch."""

    def __init__(self, reason_code, tip, observed_writer_clock, threshold):
        self.reason_code = reason_code
        self.tip_event_id = None if tip is None else tip[0]
        self.tip_recorded_at = None if tip is None else tip[2]
        self.observed_writer_clock = observed_writer_clock
        self.threshold = f"{threshold.total_seconds():g} s"
        super().__init__("; ".join(f"{key}: {value}" for key, value in self.details().items()))

    def details(self):
        return {"reason_code": self.reason_code, "tip_event_id": self.tip_event_id,
                "tip_recorded_at": self.tip_recorded_at,
                "observed_writer_clock": self.observed_writer_clock,
                "threshold": self.threshold}


def sample(clock):
    stamp = clock()
    validate_timestamp(stamp, "writer_clock")
    return stamp, datetime.fromisoformat(stamp)


class WriterBusyError(RuntimeError):
    """Another writer owns the store. A lockfile's existence is not ownership."""


def lock_path(db_path):
    return Path(str(Path(db_path).resolve()) + ".lock")


def acquire(db_path):
    # Lock even an empty file; both supported OS APIs allow locking past EOF.
    handle = lock_path(db_path).open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise WriterBusyError(f"writer already owns store: {Path(db_path).resolve()}") from exc
    return handle  # Closing or process death releases the OS lock; never unlink it.


class WriterConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        self.owner_lock = None
        self.append_lock = RLock()
        self._opened = False
        super().__init__(*args, **kwargs)
        self._opened = True
        self.clock = clock_now
        self.threshold = MAX_CLOCK_SKEW

    def close(self):
        with self.append_lock:
            try:
                if self._opened:
                    super().close()
                    self._opened = False
            finally:
                if self.owner_lock is not None:
                    self.owner_lock.close()
                    self.owner_lock = None

    def __del__(self):
        self.close()
