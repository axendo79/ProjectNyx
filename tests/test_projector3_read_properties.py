"""Seeded public-read properties for accepted ADRs 0010/0014/0024/0025/0034/0035.

Only ordinary observed claims are generated: report corrections, support changes,
identity resolution and world-validity intervals have no authority here. Explicit
IDs, times and a local Random make the complete input independent of wall clocks.
"""

from contextlib import closing
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import random

import pytest

from nyx import events, hashing, projection, storage


SEEDS = (0, 1, 2, 3, 7, 17, 42, 73, 99, 31337, 0xC0FFEE, 20261015)
EVENTS_PER_SEQUENCE = 48
BASE = datetime(2026, 7, 13, tzinfo=timezone.utc)
# Independent test oracle, intentionally not imported from nyx.forward.
ENDINGS = {
    "correction_appended": ("corrected", "corrected_by"),
    "candidate_replaced": ("replaced", "replaced_by"),
    "candidate_expired": ("expired", "expired_at"),
}


def _stamp(instant):
    return instant.isoformat().replace("+00:00", "Z")


def _instant(stamp):
    return datetime.fromisoformat(stamp)


def _bytes(value):
    return hashing.canonical_json(value).encode("utf-8")


def _generate(seed):
    rng = random.Random(seed)
    pairs, scopes, live = [], {}, {}
    candidate_number = 0
    mention_number = 0

    def emit(kind, payload):
        position = len(pairs) + 1
        # Tied recording instants exercise inclusive cutoff/chain-order semantics.
        recorded = BASE + timedelta(seconds=position // 2)
        occurred = (BASE + timedelta(days=1) if kind == "correction_appended"
                    else BASE - timedelta(seconds=rng.randrange(100)))
        pair = events.build_event(
            event_type=kind, origin_type="observed",
            source={"actor_id": f"sensor-{rng.randrange(3)}", "config": {}},
            source_class="direct_observation", occurred_at=_stamp(occurred),
            recorded_at=_stamp(recorded), event_id=f"e-{seed}-{position:03d}",
            prev_event_hash=pairs[-1][0].event_hash if pairs else None,
            payload=payload,
        )
        pairs.append(pair)
        if kind in ENDINGS:
            bid = payload.get("belief_id") or payload["claim"]["belief_id"]
            live[bid].difference_update(payload["targets"])
        claims = payload.get("claims", [])
        if "claim" in payload:
            claims = [payload["claim"]]
        for claim in claims:
            live[claim["belief_id"]].add(claim["claim_candidate_id"])

    def add_mention():
        nonlocal mention_number
        index = mention_number
        mention_number += 1
        mid, subject = f"m-{index}", f"s-{index}"
        emit("entity_mention_recorded", {
            "mention_id": mid, "subject_id": subject,
            "text": "the same device", "link_state": "constitutive",
        })
        # Exact case and Unicode property strings are opaque recorded scopes.
        for prop in ("port", "Port", "r\u00e9gion"):
            bid = f"b-{index}-{len(scopes)}"
            scopes[bid] = {"mention_id": mid, "subject_id": subject,
                           "property_id": prop, "belief_id": bid}
            live[bid] = set()

    def fresh_claim(bid, value=None):
        nonlocal candidate_number
        candidate_number += 1
        return {**scopes[bid], "claim_candidate_id": f"c-{seed}-{candidate_number:03d}",
                "value": rng.choice(("4100", "4200", "na\u00efve", "")) if value is None else value,
                "verifiability": rng.choice(("externally_checkable", "locally_checkable",
                                              "subjective", "structurally_unverifiable"))}

    def transition(kind, bid, targets):
        payload = {"targets": sorted(targets), "basis": {
            "kind": "stated_error" if kind == "correction_appended" else "stated",
            "statement": f"seed {seed}: explicit {kind}",
        }}
        if kind == "candidate_expired":
            payload["belief_id"] = bid
        else:
            payload["claim"] = fresh_claim(bid)
        emit(kind, payload)
        return payload.get("claim", {}).get("claim_candidate_id")

    # Required witnesses are present for every seed, with randomized live targets.
    add_mention()
    first = next(iter(scopes))
    emit("observation_recorded", {"claims": [fresh_claim(first, "4100"),
                                             fresh_claim(first, "4100")]})
    emit("observation_recorded", {"claims": [fresh_claim(first, "4200")]})
    successor = transition("candidate_replaced", first, rng.sample(sorted(live[first]), 2))
    successor = transition("correction_appended", first, [successor])
    transition("candidate_expired", first, [successor])
    transition("candidate_expired", first, sorted(live[first]))
    # A belief with no live candidates can accumulate fresh ordinary observations.
    emit("observation_recorded", {"claims": [fresh_claim(first)]})
    add_mention()
    add_mention()
    # Guarantee a multi-belief event, independently scoped even with equal text.
    emit("observation_recorded", {"claims": [fresh_claim(bid) for bid in scopes]})

    while len(pairs) < EVENTS_PER_SEQUENCE:
        action = rng.choice(("observation_recorded", "observation_recorded",
                             "candidate_replaced", "correction_appended",
                             "candidate_expired", "entity_mention_recorded"))
        if action == "entity_mention_recorded" and mention_number < 5:
            add_mention()
        elif action in ENDINGS and any(live.values()):
            bid = rng.choice([bid for bid in scopes if live[bid]])
            targets = rng.sample(sorted(live[bid]), rng.randint(1, len(live[bid])))
            transition(action, bid, targets)
        else:
            bids = rng.choices(list(scopes), k=rng.randint(1, 3))
            emit("observation_recorded", {"claims": [fresh_claim(bid) for bid in bids]})
    return tuple(pairs)


@pytest.fixture(scope="module", params=SEEDS, ids=lambda seed: f"seed-{seed}")
def generated(request):
    return request.param, _generate(request.param)


def _prefixes(conn, pairs):
    # ADR 0012/0014 section 7 require shared evaluation time. Use the generated
    # log's final tip for EVERY publication, rather than relabel raw live rows.
    tip = pairs[-1][0].recorded_at
    for position, pair in enumerate(pairs, 1):
        assert storage.safe_append_event(conn, *pair, "3")
        assert storage.materialize_pending(conn, tip, "3") == 1
        yield position


def _populate(conn, pairs):
    for _ in _prefixes(conn, pairs):
        pass


def _model(log):
    """Read only recorded claims and targets, independent of projected fields."""
    claims, endings = {}, {}
    for position, (envelope, payload) in enumerate(log, 1):
        created = payload.get("claims", [])
        if "claim" in payload:
            created = [payload["claim"]]
        for claim in created:
            claims[claim["claim_candidate_id"]] = claim
        if envelope.event_type in ENDINGS:
            for cid in payload["targets"]:
                assert cid not in endings, "the generator must target only live candidates"
                endings[cid] = {
                    "target_candidate_id": cid, "event_id": envelope.event_id,
                    "relation": ENDINGS[envelope.event_type][1], "log_position": position,
                }
    return claims, endings


def _decoded(pairs):
    return [(envelope, json.loads(payload.ciphertext)) for envelope, payload in pairs]


def _assert_partition(sets, bid, claims, endings):
    expected = {cid for cid, claim in claims.items() if claim["belief_id"] == bid}
    live = [candidate["claim_candidate_id"] for candidate in sets["live"]]
    retained = [item["candidate"]["claim_candidate_id"] for item in sets["retained"]]
    assert len(live) == len(set(live))
    assert len(retained) == len(set(retained))
    assert not set(live) & set(retained)
    assert set(live) | set(retained) == expected
    assert set(retained) == expected & endings.keys()
    for candidate in sets["live"]:
        assert candidate["live_status"] == "live"
        assert candidate["superseding_events"] == []
    for item in sets["retained"]:
        cid = item["candidate"]["claim_candidate_id"]
        assert item["ending_relation"] == endings[cid]
        assert item["candidate"]["superseding_events"] == [endings[cid]["event_id"]]


def test_candidate_sets_partition_and_ending_relations(generated, tmp_path):
    """ADR 0034 R9/R10/R12, sections 7-8: complete disjoint sets and one recorded ending."""
    _, pairs = generated
    with closing(storage.init_db(tmp_path / "partition.db", create=True)) as conn:
        for position in _prefixes(conn, pairs):
            log = storage.read_all_events(conn)
            claims, endings = _model(log)
            snapshot = storage.read_snapshot(conn, "3")
            assert len(log) == position
            assert set(snapshot.records("claim_candidates")) == set(claims)
            assert set(snapshot.beliefs()) == {claim["belief_id"] for claim in claims.values()}
            for bid, belief in snapshot.beliefs().items():
                sets = storage.read_candidate_sets(conn, bid, "3")
                _assert_partition(sets, bid, claims, endings)
                assert sets == snapshot.candidate_sets(bid)
                all_candidates = sets["live"] + [item["candidate"] for item in sets["retained"]]
                assert {c["claim_candidate_id"]: c for c in all_candidates} == {
                    c["claim_candidate_id"]: c for c in belief["claim_candidates"]}
                for candidate in all_candidates:
                    cid = candidate["claim_candidate_id"]
                    details = storage.read_claim_candidate_details(conn, cid, "3")
                    assert details == {"candidate": candidate, "ending_relation": endings.get(cid)}
                    assert storage.read_claim_candidate_value(conn, cid, "3") == claims[cid]["value"]
                    if cid in endings:
                        ending_event, payload = log[endings[cid]["log_position"] - 1]
                        assert cid in payload["targets"]
                        assert candidate["live_status"] == ENDINGS[ending_event.event_type][0]


def test_materialized_snapshot_equals_replay_at_every_prefix(generated, tmp_path):
    """ADR 0014 sections 1/7/9, ADR 0025 section 6, ADR 0034 durability: full equality at shared T."""
    _, pairs = generated
    tip = pairs[-1][0].recorded_at
    with closing(storage.init_db(tmp_path / "replay.db", create=True)) as conn:
        for position in _prefixes(conn, pairs):
            materialized = storage.read_snapshot(conn, "3")
            replay = projection.project_snapshot(storage.read_all_events(conn), tip, "3")
            assert materialized.complete() == replay.complete()
            assert _bytes(materialized.complete()) == _bytes(replay.complete())
            assert (materialized.log_position, materialized.event_id) == (
                position, pairs[position - 1][0].event_id)
            assert (replay.log_position, replay.event_id) == (
                materialized.log_position, materialized.event_id)


def test_as_of_never_retains_a_candidate_before_its_ending(generated, tmp_path):
    """ADR 0010 section 1 and ADR 0034 R3/section 7: inclusive recording cutoffs never rewrite history."""
    _, pairs = generated
    with closing(storage.init_db(tmp_path / "history.db", create=True)) as conn:
        _populate(conn, pairs)
        log = storage.read_all_events(conn)
    final_claims, final_endings = _model(log)
    cutoffs = sorted({instant + delta for envelope, _ in log
                      for instant in [_instant(envelope.recorded_at)]
                      for delta in (timedelta(microseconds=-1), timedelta())})
    for cutoff in cutoffs:
        included = [(envelope, payload) for envelope, payload in log
                    if _instant(envelope.recorded_at) <= cutoff]
        claims, endings = _model(included)
        snapshot = projection.project_snapshot(log, _stamp(cutoff), "3")
        assert snapshot.log_position == len(included)
        assert set(snapshot.records("claim_candidates")) == set(claims)
        for bid in {claim["belief_id"] for claim in final_claims.values()}:
            if not any(claim["belief_id"] == bid for claim in claims.values()):
                assert snapshot.candidate_sets(bid) is None
                continue
            sets = snapshot.candidate_sets(bid)
            _assert_partition(sets, bid, claims, endings)
            for item in sets["retained"]:
                ending = item["ending_relation"]
                envelope, _ = log[ending["log_position"] - 1]
                assert _instant(envelope.recorded_at) <= cutoff
            live = {candidate["claim_candidate_id"] for candidate in sets["live"]}
            for cid, ending in final_endings.items():
                ending_time = _instant(log[ending["log_position"] - 1][0].recorded_at)
                if cid in claims and claims[cid]["belief_id"] == bid and cutoff < ending_time:
                    assert cid in live


def test_public_belief_reads_never_choose_a_winner(generated, tmp_path):
    """ADR 0024 sections 1-3 and ADR 0034 R10/section 7: scalar refusal, including agreeing/live/retained claims."""
    _, pairs = generated
    saw_agreement = saw_disagreement = saw_empty_live = False
    with closing(storage.init_db(tmp_path / "no-winner.db", create=True)) as conn:
        for _ in _prefixes(conn, pairs):
            snapshot = storage.read_snapshot(conn, "3")
            for bid, belief in snapshot.beliefs().items():
                ids = {candidate["claim_candidate_id"] for candidate in belief["claim_candidates"]}
                reads = (storage.read_belief(conn, bid, "3"),
                         storage.read_belief_status(conn, bid, "3")["belief"],
                         snapshot.current_belief(belief["subject_id"], belief["property_id"]))
                for read in reads:
                    assert "current_value" not in read
                    assert {candidate["claim_candidate_id"] for candidate in read["claim_candidates"]} == ids
                sets = storage.read_candidate_sets(conn, bid, "3")
                live_values = [candidate["value"] for candidate in sets["live"]]
                saw_empty_live |= not live_values
                if len(live_values) > 1:
                    saw_agreement |= len(set(live_values)) == 1
                    saw_disagreement |= len(set(live_values)) > 1
                # Section 7 counts retained candidates too, even with <= 1 live.
                if len(ids) > 1:
                    with pytest.raises(ValueError, match="scalar"):
                        storage.read_belief_scalar(conn, bid, "3")
    assert saw_agreement and saw_disagreement and saw_empty_live


def _database_bytes(path):
    # WAL contains durable database pages; SHM is SQLite reader bookkeeping.
    # A newly created empty WAL contributes no database bytes.
    wal = path.with_name(path.name + "-wal")
    return path.read_bytes(), wal.read_bytes() if wal.exists() else b""


@pytest.mark.parametrize("active_writer", (False, True), ids=("closed-writer", "active-wal-writer"))
def test_open_readonly_public_reads_preserve_database_bytes(generated, tmp_path, active_writer):
    """ADR 0011 supported-reopen preservation, ADR 0030 section 1, ADR 0025 section 5: reads never publish/write."""
    _, pairs = generated
    path = tmp_path / "read only # store.db"
    with closing(storage.init_db(path, create=True)) as conn:
        _populate(conn, pairs)
        if not active_writer:
            conn.close()
        before = _database_bytes(path)
        with closing(storage.open_readonly(path)) as reader:
            reader.execute("BEGIN")
            storage.require_projector_schema(reader, "3")
            assert storage.read_store_metadata(reader)["event_count"] == len(pairs)
            assert storage.read_projection_status(reader, "3")["stale"] is False
            snapshot = storage.read_snapshot(reader, "3")
            log = storage.read_all_events(reader)
            for bid, belief in snapshot.beliefs().items():
                assert storage.read_belief(reader, bid, "3")["stale"] is False
                assert storage.read_belief_status(reader, bid, "3")["belief"] == belief
                assert storage.lookup_current_belief_id(
                    reader, belief["subject_id"], belief["property_id"], "3") == bid
                assert storage.read_candidate_sets(reader, bid, "3") == snapshot.candidate_sets(bid)
            for cid, candidate in snapshot.records("claim_candidates").items():
                assert storage.read_claim_candidate(reader, cid, "3") == candidate
                assert storage.read_claim_candidate_value(reader, cid, "3") == candidate["value"]
                assert storage.read_claim_candidate_details(reader, cid, "3")["candidate"] == candidate
            for kind, read, status in (
                ("entities", storage.read_entity, storage.read_entity_status),
                ("mentions", storage.read_mention, storage.read_mention_status),
                ("entity_links", storage.read_entity_link, storage.read_entity_link_status),
            ):
                for identifier, record in snapshot.records(kind).items():
                    assert read(reader, identifier, "3") == record
                    assert status(reader, identifier, "3")["record"] == record
            # Explicit historical reconstruction is also a read-only operation.
            projection.project_snapshot(log, pairs[len(pairs) // 2][0].recorded_at, "3").complete()
            assert _database_bytes(path) == before
        assert _database_bytes(path) == before


def test_same_seed_produces_byte_identical_snapshots(generated, tmp_path):
    """ADR 0010 consequences, ADR 0014 section 6, ADR 0025 sections 2/6: deterministic inputs and complete bytes."""
    seed, first = generated
    second = _generate(seed)
    assert _bytes([[asdict(envelope), asdict(payload)] for envelope, payload in first]) == _bytes(
        [[asdict(envelope), asdict(payload)] for envelope, payload in second])
    serializations = []
    for run, pairs in enumerate((first, second)):
        with closing(storage.init_db(tmp_path / f"determinism-{run}.db", create=True)) as conn:
            serializations.append([_bytes(storage.read_snapshot(conn, "3").complete())
                                   for _ in _prefixes(conn, pairs)])
    assert serializations[0] == serializations[1]
    tip = first[-1][0].recorded_at
    assert serializations[0][-1] == _bytes(projection.project_snapshot(_decoded(first), tip, "3").complete())
