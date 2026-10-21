"""Seeded generators of structured field text for the fuzz and oracle tests (hand-written)."""

from __future__ import annotations

import base64
import random

# Every character the Dictionary grammar gives a meaning to, plus a few it never allows.
ALPHABET = 'ui=,; ()"\\:?@%*.-_/!#~ \t0123456789aAzZ+\x7f\x00\xe9'
_KEY_START = "abcdefghijklmnopqrstuvwxyz*"
_KEY_REST = _KEY_START + "0123456789_-."
_TOKEN_REST = "abcXYZ019!#$%&'*+-.^_`|~:/"


def key(rng: random.Random) -> str:
    return rng.choice(_KEY_START) + "".join(rng.choice(_KEY_REST) for _ in range(rng.randint(0, 4)))


def bare_item(rng: random.Random) -> str:
    kind = rng.randrange(9)
    if kind == 0:
        return str(rng.randint(-(10**15) + 1, 10**15 - 1))
    if kind == 1:
        whole = rng.randint(0, 10**12 - 1)
        return f"{rng.choice(['', '-'])}{whole}.{rng.randint(0, 999):0{rng.randint(1, 3)}d}"[:17]
    if kind == 2:
        inner = "".join(rng.choice(' az"\\~!') for _ in range(rng.randint(0, 6)))
        return '"' + inner.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if kind == 3:
        return rng.choice("aZ*") + "".join(
            rng.choice(_TOKEN_REST) for _ in range(rng.randint(0, 5))
        )
    if kind == 4:
        text = base64.b64encode(rng.randbytes(rng.randint(0, 7))).decode()
        return ":" + (text.rstrip("=") if rng.random() < 0.3 else text) + ":"
    if kind == 5:
        return rng.choice(["?0", "?1"])
    if kind == 6:
        return "@" + str(rng.randint(-(10**10), 10**10))
    if kind == 7:
        octets = rng.choice([b"", b"caf\xc3\xa9", b"\xe2\x82\xac", b"%\x22", b"\xc3", b"a b"])
        body = "".join(f"%{o:02x}" if o in (0x22, 0x25) or o > 0x7E else chr(o) for o in octets)
        return '%"' + body + '"'
    return "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 3)))


def params(rng: random.Random) -> str:
    out = ""
    for _ in range(rng.choice([0, 0, 1, 2])):
        out += ";" + rng.choice(["", " "]) + key(rng)
        if rng.random() < 0.7:
            out += "=" + bare_item(rng)
    return out


def member(rng: random.Random) -> str:
    name = key(rng)
    shape = rng.randrange(4)
    if shape == 0:
        return name + params(rng)
    if shape == 1:
        items = [bare_item(rng) + params(rng) for _ in range(rng.randint(0, 3))]
        pad = rng.choice(["", " "])
        return f"{name}=({pad}{' '.join(items)}{pad}){params(rng)}"
    return f"{name}={bare_item(rng)}{params(rng)}"


def dictionary(rng: random.Random) -> str:
    """A Dictionary that follows the grammar, with optional whitespace in the allowed places."""
    separators = [rng.choice([",", ", ", " ,\t", "\t, "]) for _ in range(5)]
    members = [member(rng) for _ in range(rng.randint(0, 5))]
    text = members[0] if members else ""
    for index, item in enumerate(members[1:]):
        text += separators[index] + item
    return rng.choice(["", " ", "  "]) + text + rng.choice(["", " ", " \t"])


def mutated(rng: random.Random, text: str) -> str:
    """Insert, delete or replace one character, so the text sits just off the grammar."""
    where = rng.randint(0, len(text))
    op = rng.randrange(3)
    if op == 0 or not text:
        return text[:where] + rng.choice(ALPHABET) + text[where:]
    where = min(where, len(text) - 1)
    if op == 1:
        return text[:where] + text[where + 1 :]
    return text[:where] + rng.choice(ALPHABET) + text[where + 1 :]


def field(rng: random.Random) -> str:
    """One case: valid, one edit away from valid, or noise over the alphabet."""
    roll = rng.random()
    if roll < 0.4:
        return dictionary(rng)
    if roll < 0.8:
        return mutated(rng, dictionary(rng))
    return "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 30)))
