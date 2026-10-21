"""PRIORITY_UPDATE frames against independent implementations: hyperframe and aioquic.

Neither is a dependency; each test skips when its oracle is not installed (``pip install
hyperframe aioquic``). The versions used for the 1.0.0 certification are in
CERT-1.0-REPORT.md.
"""

from __future__ import annotations

import random

import pytest
import sfgen

from priorityheader import PriorityError, decode_h3_update, encode_h2_update, encode_h3_update
from priorityheader._h3 import decode_varint, encode_varint
from priorityheader._sfdict import parse_dictionary


def test_h2_frames_parse_with_hyperframe() -> None:
    frame_module = pytest.importorskip("hyperframe.frame")
    rng = random.Random(6)
    for _ in range(3_000):
        stream = rng.choice([1, 2**31 - 1, rng.randint(1, 2**31 - 1)])
        value = sfgen.dictionary(rng).strip(" \t")
        try:
            parse_dictionary(value)
        except PriorityError:
            continue
        data = encode_h2_update(stream, value, max_frame_size=2**24 - 1)
        frame, length = frame_module.Frame.parse_frame_header(memoryview(data[:9]))
        frame.parse_body(memoryview(data[9:]))
        assert (frame.type, frame.stream_id, frame.flag_byte, length) == (0x10, 0, 0, len(data) - 9)
        assert frame.body == stream.to_bytes(4, "big") + value.encode("ascii")


def test_h3_frames_and_varints_match_aioquic() -> None:
    connection = pytest.importorskip("aioquic.h3.connection")
    buffer = pytest.importorskip("aioquic.buffer")
    rng = random.Random(7)
    for _ in range(3_000):
        number = rng.choice([rng.randint(0, 63), rng.randint(0, 2**14), rng.randint(0, 2**62 - 1)])
        assert encode_varint(number) == buffer.encode_uint_var(number)
        assert decode_varint(buffer.encode_uint_var(number)) == (number, len(encode_varint(number)))
        target = rng.choice(["stream", "push"])
        element = number - number % 4 if target == "stream" else number
        kind = 0xF0700 if target == "stream" else 0xF0701
        value = rng.choice(["", "u=1", "u=7, i", "x=(1 2);p, i=?0"])
        expected = connection.encode_frame(kind, buffer.encode_uint_var(element) + value.encode())
        assert encode_h3_update(element, value, target=target) == expected  # type: ignore[arg-type]
        decoded = decode_h3_update(expected)
        assert (decoded.element_id, decoded.field_value, decoded.target) == (element, value, target)
