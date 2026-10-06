"""A-G5: every §1a must-equal field class, both sides, ADR 0034 §1a.

Enumerate every scalar and empty collection in the complete ordinary fixture,
including all nested candidate, dependency and identity copies. This also guards
new fields automatically; only the precisely permitted lineage/status paths
are excluded. Inventory and collection membership have separate mutations.
"""
from copy import deepcopy
from contextlib import closing
from dataclasses import replace
import pytest
from nyx import committed, forward, integrity, merkle, projection, storage
from test_event_integrity import entries
from test_reducer_boundary import T2, claim, decoded, event, mention
from test_verify_store import verifier


LOG = decoded(entries("2"))
OLD = projection.project_snapshot(LOG, T2, "2")
NEW = projection.project_snapshot(LOG, T2, "3")


def paths(value, path=()):
    if len(path) == 3 and path[0] == "beliefs" and path[-1] == "view_version_hash":
        return
    if path and path[-1] == "live_status":
        return
    if isinstance(value, dict) and value:
        for key, member in value.items():
            yield from paths(member, path + (key,))
    elif isinstance(value, list) and value:
        for index, member in enumerate(value):
            yield from paths(member, path + (index,))
    else:
        yield path


FIELDS = list(paths(NEW.complete()))


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("path", FIELDS, ids=lambda p: "/".join(map(str, p)))
def test_ag5_every_complete_field_mutation_rejects(side, path):
    old, new = deepcopy(OLD.complete()), deepcopy(NEW.complete())
    changed = old if side == "old" else new
    parent = changed
    for part in path[:-1]:
        parent = parent[part]
    original = parent[path[-1]]
    parent[path[-1]] = ({"unexpected": "mutation"} if isinstance(original, dict)
                       else ["mutation"] if isinstance(original, list) else "mutation")
    assert parent[path[-1]] != original
    with pytest.raises(ValueError, match="equivalence"):
        forward.assert_semantically_equivalent_values(old, new)


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("kind", list(NEW.complete()))
def test_ag5_record_inventory_ids_must_equal(side, kind):
    old, new = deepcopy(OLD.complete()), deepcopy(NEW.complete())
    changed = old if side == "old" else new
    records = changed[kind]
    key = next(iter(records))
    records["reminted-record-key"] = records.pop(key)
    with pytest.raises(ValueError, match="equivalence"):
        forward.assert_semantically_equivalent_values(old, new)


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("collection", committed.COLLECTIONS)
def test_ag5_belief_collection_membership_must_equal(side, collection):
    old, new = deepcopy(OLD.complete()), deepcopy(NEW.complete())
    changed = old if side == "old" else new
    changed["beliefs"]["b-a"][collection].pop()
    with pytest.raises(ValueError, match="equivalence"):
        forward.assert_semantically_equivalent_values(old, new)


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("field", ["log_position", "event_id"])
def test_ag5_applied_progress_must_equal_on_both_sides(side, field):
    old, new = OLD, NEW
    changed = replace(old if side == "old" else new,
                      **{field: 2 if field == "log_position" else "wrong-tip"})
    with pytest.raises(ValueError, match="progress"):
        forward.assert_semantically_equivalent(changed if side == "old" else old,
                                              changed if side == "new" else new)


@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("status", ["corrected", "replaced", "expired"])
def test_ag5_nonlive_status_never_a_permitted_difference(side, nested, status):
    old, new = deepcopy(OLD.complete()), deepcopy(NEW.complete())
    changed = old if side == "old" else new
    candidate = changed["beliefs"]["b-a"]["claim_candidates"][0] if nested else changed["claim_candidates"]["c-a"]
    candidate["live_status"] = status
    with pytest.raises(ValueError, match="live"):
        forward.assert_semantically_equivalent_values(old, new)


def test_ag5_only_permitted_lineage_and_live_status_differences_pass():
    assert OLD.header("b-a")["view_version_hash"] != NEW.header("b-a")["view_version_hash"]
    assert merkle.digest(OLD.roots["beliefs"]) != merkle.digest(NEW.roots["beliefs"])
    forward.assert_semantically_equivalent(OLD, NEW)
    old = deepcopy(OLD.complete())
    for candidate in [*old["claim_candidates"].values(), *old["beliefs"]["b-a"]["claim_candidates"]]:
        candidate["live_status"] = "live"
    forward.assert_semantically_equivalent_values(old, NEW.complete())
    for snapshot in (OLD, NEW):
        assert committed.full_result_roots(snapshot.belief("b-a")) == snapshot.header("b-a")["collection_roots"]
    forward.verify_lineage(LOG, T2)


@pytest.mark.parametrize("nested", [False, True])
def test_ag5_new_side_added_live_status_is_required(nested):
    changed = deepcopy(NEW.complete())
    candidate = changed["beliefs"]["b-a"]["claim_candidates"][0] if nested else changed["claim_candidates"]["c-a"]
    del candidate["live_status"]
    with pytest.raises(ValueError, match="live"):
        forward.assert_semantically_equivalent_values(OLD.complete(), changed)


@pytest.mark.parametrize("version", ["2", "3"])
def test_ag5_each_versions_own_lineage_is_independently_verified(tmp_path, version):
    path = tmp_path / "lineage.db"
    with closing(storage.init_db(path, create=True)) as conn:
        for pair in entries("2"):
            storage.safe_append_event(conn, *pair, version)
            storage.materialize_pending(conn, T2, version)
        report = verifier["verify_store"](path, version)
        assert report["ok"] and report["checked"]["lineage"] > 0, report


@pytest.mark.parametrize("damage", ["extra", "missing", "nonconstitutive", "unknown-event", "unknown-origin"])
def test_ag5_transition_free_refusals_match(damage):
    data = {"claims": [claim()]}
    kind, changes = "observation_recorded", {}
    prefix = [event("entity_mention_recorded", mention())]
    if damage == "extra": data["claims"][0]["extra"] = True
    elif damage == "missing": del data["claims"][0]["subject_id"]
    elif damage == "nonconstitutive":
        prefix, kind, data = [], "entity_mention_recorded", {**mention(), "link_state": "speculative"}
    elif damage == "unknown-event": kind = "gap_recorded"
    else: changes["origin_type"] = "unknown-origin"
    pair = event(kind, data, len(prefix) + 1, prefix[-1] if prefix else None, **changes)
    refusals = []
    for version in ("2", "3"):
        with pytest.raises((ValueError, NotImplementedError, integrity.IntegrityError)) as refusal:
            projection.project_snapshot(decoded(prefix + [pair]), T2, version)
        refusals.append((type(refusal.value), str(refusal.value)))
    assert refusals[0] == refusals[1]
