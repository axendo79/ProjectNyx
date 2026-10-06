"""A-G1: independent origin taxonomy, ADR 0034 §§1/10; V0 §4 envelope enum."""
from contextlib import closing
from dataclasses import asdict

import pytest

from nyx import events, integrity, storage
from test_forward_correction import append, initial_log
from test_reducer_boundary import event
from test_verify_store import verifier


@pytest.mark.parametrize("origin, expected_ok", [("unknown-expiry-origin", False), ("personal", True)])
def test_a_g1_consistently_rehashed_expiry_origin(tmp_path, monkeypatch, origin, expected_ok):
    """A-G1: enum admission is distinct from an origin-to-standing mapping."""
    log = initial_log()
    payload = {"belief_id": "b-a", "targets": ["c-A"],
               "basis": {"kind": "stated", "statement": "invented state ended"}}
    original = event(events.CANDIDATE_EXPIRED, payload, 3, log[-1])
    rewritten = event(events.CANDIDATE_EXPIRED, payload, 3, log[-1], origin_type=origin)
    assert asdict(rewritten[0]) == {**asdict(original[0]), "origin_type": origin,
                                   "event_hash": rewritten[0].event_hash}
    assert rewritten[0].event_hash != original[0].event_hash
    path = tmp_path / "origin.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        if not expected_ok:
            with pytest.raises(integrity.IntegrityError, match="unknown origin_type"):
                integrity.validate_event(rewritten[0], payload)
        # A disposable forgery fixture: bypass ONLY the enum while constructing
        # fully consistent Layer-A hashes and derived commitments. Restore it
        # before the independent audit; hash/lineage errors cannot mask the gap.
        with monkeypatch.context() as fixture:
            fixture.setattr(integrity, "ORIGINS", integrity.ORIGINS | {origin})
            append(conn, rewritten)
    result = verifier["verify_store"](path, "3")
    assert result["ok"] is expected_ok, result
    if not expected_ok:
        assert any(item["check"] == "event_schema" and "origin" in item["message"]
                   for item in result["failures"]), result
        assert not any(item["check"] in ("envelope_hash", "payload_hash", "merkle", "lineage")
                       for item in result["failures"]), result
