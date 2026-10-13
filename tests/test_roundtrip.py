"""Seeded random round trips and random input. The data is generated here, not sourced."""

from __future__ import annotations

import random
import string
from decimal import Decimal

from priorityheader import (
    Date,
    DisplayString,
    ExtensionValue,
    Priority,
    PriorityError,
    PriorityParams,
    Token,
    build_params,
    build_priority,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    encode_h3_update,
    parse_params,
    parse_priority,
)

KEY_REST = string.ascii_lowercase + string.digits + "_-.*"


def _key(rng: random.Random) -> str:
    first = rng.choice(string.ascii_lowercase + "*")
    key = first + "".join(rng.choice(KEY_REST) for _ in range(rng.randint(0, 4)))
    return key if key not in ("u", "i") else key + "x"


def _bare(rng: random.Random) -> int | Decimal | str | bytes:
    kind = rng.randrange(8)
    if kind == 0:
        return rng.random() < 0.5
    if kind == 1:
        return rng.randint(-(10**15) + 1, 10**15 - 1)
    if kind == 2:
        return Decimal(rng.randint(-(10**15) + 1, 10**15 - 1)) / 1000
    if kind == 3:
        return "".join(chr(rng.randint(0x20, 0x7E)) for _ in range(rng.randint(0, 8)))
    if kind == 4:
        return Token(rng.choice(string.ascii_letters + "*") + "".join(rng.choices("a:/!#9", k=3)))
    if kind == 5:
        return bytes(rng.randrange(256) for _ in range(rng.randint(0, 6)))
    if kind == 6:
        return Date(rng.randint(-(10**15) + 1, 10**15 - 1))
    return DisplayString("".join(chr(rng.randint(0x20, 0x2FF)) for _ in range(rng.randint(0, 5))))


def _params(rng: random.Random) -> PriorityParams:
    extensions: dict[str, ExtensionValue] = {}
    for _ in range(rng.randint(0, 4)):
        value: ExtensionValue = _bare(rng)
        if rng.random() < 0.2:
            value = tuple(_bare(rng) for _ in range(rng.randint(0, 3)))
        extensions[_key(rng)] = value
    urgency = rng.choice([None, *range(8)])
    incremental = rng.choice([None, True, False])
    return PriorityParams(urgency, incremental, extensions)


def test_build_params_round_trips_random_structures() -> None:
    rng = random.Random(9218)
    for _ in range(3000):
        params = _params(rng)
        assert parse_params(build_params(params), strict=True) == params


def test_build_priority_round_trips_random_values() -> None:
    rng = random.Random(9651)
    for _ in range(1000):
        priority = Priority(rng.randint(0, 7), rng.random() < 0.5)
        params = _params(rng)
        text = build_priority(*priority, extensions=params.extensions)
        assert parse_priority(text, strict=True) == priority
        assert parse_params(text).extensions == params.extensions


def test_frames_round_trip_random_values() -> None:
    rng = random.Random(7)
    for _ in range(500):
        value = build_params(_params(rng))
        stream = rng.randint(1, 2**31 - 1)
        assert decode_h2_update(encode_h2_update(stream, value)).field_value == value
        element = rng.randint(0, 2**60) * 4
        assert decode_h3_update(encode_h3_update(element, value)).element_id == element


def test_random_text_never_raises_in_lenient_mode() -> None:
    rng = random.Random(42)
    alphabet = 'ui=,;?01 \t"\\():*@%-.aZ:\xe9\r\n'
    for _ in range(5000):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 16)))
        priority = parse_priority(text)
        assert 0 <= priority.urgency <= 7
        try:
            assert parse_priority(text, strict=True) == priority
        except PriorityError as error:
            assert error.offset is not None and 0 <= error.offset <= len(text)
            assert priority == Priority()


def test_random_octets_never_crash_the_frame_decoders() -> None:
    rng = random.Random(3)
    for _ in range(5000):
        data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 20)))
        for decode in (decode_h2_update, decode_h3_update):
            try:
                update = decode(data)
            except PriorityError:
                continue
            assert update.element_id >= 0
            update.priority()
