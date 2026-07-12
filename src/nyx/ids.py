"""Identifier generation.

spec/NYX_V0_IMPLEMENTATION.md §1 — Event ID: UUIDv7 (time-ordered UUID). Any
time-sortable unique id satisfies the ordering requirement of §1; UUIDv7 is the
standard choice. Implemented per RFC 9562 with the standard library only (no
dependency, and independent of whether the running Python ships uuid.uuid7).
"""

from __future__ import annotations

import os
import time
import uuid


def new_event_id() -> str:
    """Return a fresh time-ordered event id (UUIDv7 string).

    Layout (RFC 9562): 48-bit Unix-ms timestamp | version(7) | 12 rand bits |
    variant(0b10) | 62 rand bits. Time-sortable, which is all §1 requires.
    """
    unix_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF          # 12 bits
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF  # 62 bits
    value = unix_ms << 80
    value |= 0x7 << 76        # version 7
    value |= rand_a << 64
    value |= 0b10 << 62       # RFC 4122 variant
    value |= rand_b
    return str(uuid.UUID(int=value))
