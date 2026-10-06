"""B03: exact adversarial IDs and UTF-8 set order, ADR 0034 §3/0014 §6."""
from contextlib import closing
import pytest
from nyx import projection, storage
from queue13_helpers import assert_prefix, canonical_ids, contents, payload
from test_forward_correction import append
from test_reducer_boundary import T2, claim, decoded, event, mention


@pytest.mark.parametrize("kind", ["correction_appended", "candidate_replaced", "candidate_expired"])
def test_b03_identifier_bytes_are_preserved_and_noncanonical_targets_refuse(tmp_path, kind):
    ids = ["é", "e\u0301", "line\nfeed", 'quote"', "back\\slash", "x" * 8192]
    ordered = canonical_ids(ids)
    assert len(ordered) == 6 and "é" != "e\u0301"
    log = [event("entity_mention_recorded", mention())]
    log.append(event("observation_recorded", {"claims": [claim(cid) for cid in ids]}, 2, log[-1]))
    bad = event(kind, payload(kind, list(reversed(ordered))), 3, log[-1])
    good = event(kind, payload(kind, ordered), 3, log[-1])
    path = tmp_path / "bytes.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in log:
            append(conn, pair)
        before = contents(conn)
        assert set(storage.read_snapshot(conn, "3").records("claim_candidates")) == set(ids)
        with pytest.raises(ValueError, match="canonically sorted"):
            storage.safe_append_event(conn, *bad, "3")
        assert contents(conn) == before
        with pytest.raises(ValueError, match="canonically sorted"):
            projection.project_snapshot(decoded(log + [bad]), T2, "3")
        append(conn, good)
        assert_prefix(conn, path, log + [good])
        retained = storage.read_candidate_sets(conn, "b-a", "3")["retained"]
        assert {item["candidate"]["claim_candidate_id"] for item in retained} == set(ids)
