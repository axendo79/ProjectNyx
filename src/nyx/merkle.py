"""Canonical persistent compressed binary map, byte contract in ADR 0025."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Callable

from . import hashing

FORMAT = "nyx-map/1"
EMPTY = hashing._sha256_hex(hashing.canonical_json({"format": FORMAT, "kind": "empty"}))


@dataclass(frozen=True)
class Node:
    digest: str
    raw: str
    bit: int
    prefix: int
    key: str | None = None
    value: str | None = None
    left: Tree = None
    right: Tree = None
    # In-memory references for roots explicitly committed inside a leaf value.
    # They are not additional hash inputs and cannot change the encoded value.
    links: object = field(default_factory=lambda: MappingProxyType({}), compare=False)

    def resolve(self):
        return self


@dataclass(frozen=True)
class Reference:
    digest: str
    loader: Callable[[str], Node] = field(compare=False, repr=False)

    def resolve(self):
        return self.loader(self.digest)


type Tree = Node | Reference | None


def digest(tree: Tree) -> str:
    return EMPTY if tree is None else tree.digest


def valid_hash(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def route(key: str) -> int:
    if not isinstance(key, str) or not key:
        raise ValueError("Merkle map keys must be nonempty strings")
    return int(hashing._sha256_hex(hashing.canonical_json(key)), 16)


def prefix(bits: int, length: int) -> int:
    return (bits >> (256 - length)) << (256 - length)


def direction(bits: int, bit: int) -> int:
    return (bits >> (255 - bit)) & 1


def _create(body, bit, routing, written, **fields):
    raw = hashing.canonical_json({"format": FORMAT, **body})
    node = Node(hashing._sha256_hex(raw), raw, bit, routing, **fields)
    if written is not None:
        written[node.digest] = raw
    return node


def _leaf(key, value, written, links):
    raw_value = hashing.canonical_json(value)
    return _create({"kind": "leaf", "key": key, "value": json.loads(raw_value)},
                   -1, route(key), written, key=key, value=raw_value,
                   links=MappingProxyType(dict(links or {})))


def _branch(bit, common, left, right, written):
    if left is None or right is None:
        return right if left is None else left
    common = prefix(common, bit)
    return _create({"kind": "branch", "bit": bit, "prefix": f"{common:064x}",
                    "left": digest(left), "right": digest(right)},
                   bit, common, written, left=left, right=right)


def _child(node, side):
    child = (node.right if side else node.left).resolve()
    if (prefix(child.prefix, node.bit) != node.prefix
            or direction(child.prefix, node.bit) != side
            or (child.bit >= 0 and child.bit <= node.bit)):
        raise ValueError("invalid Merkle child routing")
    return child


def get_leaf(tree: Tree, key: str) -> Node | None:
    bits = route(key)
    while tree is not None:
        node = tree.resolve()
        if node.bit < 0:
            return node if node.key == key else None
        if prefix(bits, node.bit) != node.prefix:
            return None
        tree = _child(node, direction(bits, node.bit))
    return None


def get(tree: Tree, key: str):
    node = get_leaf(tree, key)
    return None if node is None else json.loads(node.value)


def put(tree: Tree, key: str, value, written=None, *, links=None) -> Node:
    bits = route(key)
    if tree is None:
        return _leaf(key, value, written, links)
    node = tree.resolve()
    if node.bit < 0 and node.key == key:
        if node.value == hashing.canonical_json(value):
            return node
        return _leaf(key, value, written, links)
    different = 256 - (bits ^ node.prefix).bit_length()
    if node.bit < 0 and different == 256:
        raise ValueError("distinct Merkle keys have a routing hash collision")
    if node.bit < 0 or different < node.bit:
        leaf = _leaf(key, value, written, links)
        left, right = (node, leaf) if direction(bits, different) else (leaf, node)
        return _branch(different, bits, left, right, written)
    side = direction(bits, node.bit)
    child = _child(node, side)
    updated = put(child, key, value, written, links=links)
    if updated.digest == child.digest:
        return node
    return _branch(node.bit, node.prefix, node.left if side else updated,
                   updated if side else node.right, written)


def delete(tree: Tree, key: str, written=None) -> Tree:
    bits = route(key)
    if tree is None:
        return None
    node = tree.resolve()
    if node.bit < 0:
        return None if node.key == key else node
    if prefix(bits, node.bit) != node.prefix:
        return node
    side = direction(bits, node.bit)
    child = _child(node, side)
    updated = delete(child, key, written)
    if digest(updated) == child.digest:
        return node
    return _branch(node.bit, node.prefix, node.left if side else updated,
                   updated if side else node.right, written)


def items(tree: Tree):
    if tree is None:
        return
    node = tree.resolve()
    if node.bit < 0:
        yield node.key, json.loads(node.value)
    else:
        yield from items(_child(node, 0))
        yield from items(_child(node, 1))


def rebuild(values):
    tree = None
    for key, value in values:
        tree = put(tree, key, value)
    return tree


def prove(tree: Tree, key: str) -> list[dict]:
    bits = route(key)
    proof = []
    while tree is not None:
        node = tree.resolve()
        if node.bit < 0:
            if node.key != key:
                break
            return proof
        if prefix(bits, node.bit) != node.prefix:
            break
        body = json.loads(node.raw)
        proof.append({k: body[k] for k in ("bit", "prefix", "left", "right")})
        tree = _child(node, direction(bits, node.bit))
    raise KeyError(key)


def verify(root: str, key: str, value, proof: list[dict]) -> bool:
    """Membership against a caller-trusted root; not an exhaustive state audit."""
    try:
        bits = route(key)
        if not valid_hash(root) or not isinstance(proof, list) or len(proof) > 256:
            return False
        last_bit = -1
        for step in proof:
            if not isinstance(step, dict) or set(step) != {"bit", "prefix", "left", "right"}:
                return False
            bit = step["bit"]
            if (type(bit) is not int or not last_bit < bit < 256
                    or not valid_hash(step["prefix"])
                    or int(step["prefix"], 16) != prefix(bits, bit)
                    or any(not valid_hash(step[s]) or step[s] == EMPTY for s in ("left", "right"))):
                return False
            last_bit = bit
        current = _leaf(key, value, None, None).digest
        for step in reversed(proof):
            side = "right" if direction(bits, step["bit"]) else "left"
            if step[side] != current:
                return False
            current = hashing._sha256_hex(hashing.canonical_json(
                {"format": FORMAT, "kind": "branch", **step}))
        return current == root
    except (TypeError, ValueError, KeyError):
        return False


def decode(raw: str, expected: str, loader) -> Node:
    """Validate a content-addressed node before exposing it to traversal."""
    body = json.loads(raw)
    if (hashing.canonical_json(body) != raw or hashing._sha256_hex(raw) != expected
            or not isinstance(body, dict) or body.get("format") != FORMAT):
        raise ValueError("corrupt Merkle node")
    if body.get("kind") == "leaf" and set(body) == {"format", "kind", "key", "value"}:
        return Node(expected, raw, -1, route(body["key"]), key=body["key"],
                    value=hashing.canonical_json(body["value"]))
    if body.get("kind") == "branch" and set(body) == {"format", "kind", "bit", "prefix", "left", "right"}:
        bit = body["bit"]
        if (type(bit) is not int or not 0 <= bit < 256 or not valid_hash(body["prefix"])
                or int(body["prefix"], 16) != prefix(int(body["prefix"], 16), bit)
                or any(not valid_hash(body[s]) or body[s] == EMPTY for s in ("left", "right"))):
            raise ValueError("invalid Merkle branch")
        return Node(expected, raw, bit, int(body["prefix"], 16),
                    left=Reference(body["left"], loader), right=Reference(body["right"], loader))
    raise ValueError("invalid Merkle node encoding")


def detach(tree: Tree, cache=None) -> Tree:
    """Retain immutable nodes, removing all transaction-bound lazy references."""
    if tree is None:
        return None
    if cache is None:
        cache = {}
    if tree.digest in cache:
        return cache[tree.digest]
    node = tree.resolve()
    detached = replace(node, left=detach(node.left, cache), right=detach(node.right, cache),
                       links=MappingProxyType({k: detach(v, cache) for k, v in node.links.items()}))
    cache[node.digest] = detached
    return detached
