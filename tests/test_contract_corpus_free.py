"""Contracts that hold without the fetched corpus, from the QA mutation round.

Each case was written by hand from the RFC 9651 and RFC 9218 grammar; the fetched httpwg
corpus covers the same ground, but its tests skip in a fresh clone.
"""

from __future__ import annotations

import pytest

from priorityheader import (
    Date,
    FrameError,
    Priority,
    PriorityError,
    PriorityParams,
    Token,
    build_params,
    build_priority,
    decode_h2_update,
    decode_h3_update,
    parse_params,
    parse_priority,
)


@pytest.mark.parametrize(
    "text,offset",
    [
        ('a=%"%C3%A9"', 5),  # RFC 9651 section 4.2.10: escapes are lower-case hex
        ('a=(1"x")', 4),  # section 4.2.1.2: inner list members are separated by spaces
        ("x=(\t1)", 3),  # section 4.2.1.2: only SP, never HTAB, inside an inner list
        ("x=(1\t2)", 4),
        ("x=(1 \t)", 5),
        ('a=%"%ff"', 8),  # section 4.2.10: a Display String must decode as UTF-8
        ("a=@1.5", 6),  # section 4.2.9: a Date is an Integer
        ("aB=1", 1),  # section 4.2.3.3: a key holds no upper-case letter
        ("a=1.", 4),  # section 4.2.4: a Decimal has 1 to 3 digits after the point
        ("a=-1.", 5),
        ("u=1., i", 4),
        ("a=? 1", 3),  # section 4.2.8: no space inside a Boolean
        ("a=(? 0)", 4),
        ("i=? 1", 3),
        ("u=1;\ta=2, i", 4),  # section 4.2.3.2: only SP, never HTAB, after a ';'
        ("a=(1;\tb)", 5),
        ("i;\tx", 2),
        (r'a="\n"', 5),  # section 4.2.5: only a quote or a backslash follows a backslash
        (r'u=1, a="x\ny"', 11),
        (r'a=("\n")', 6),
    ],
)
def test_strict_parse_refuses_grammar_breaks_at_their_offset(text: str, offset: int) -> None:
    with pytest.raises(PriorityError) as caught:
        parse_params(text, strict=True)
    assert caught.value.offset == offset
    assert parse_params(text).extensions == {}
    assert parse_priority(text) == Priority()


@pytest.mark.parametrize(
    "text", ["u=1; a=2, i", "u=1;  a, i", "u=1,\ti", "u=1 ,\t i", "u=1,\t\t i"]
)
def test_spaces_after_a_semicolon_and_tabs_around_a_comma_are_read(text: str) -> None:
    # Section 4.2.3.2 skips SP after ';'; section 4.2.2 allows OWS (SP or HTAB) around ','.
    assert parse_priority(text, strict=True) == Priority(1, True)


@pytest.mark.parametrize("key", ["1a", "A", "-a", "a!", ""])
def test_the_writer_refuses_keys_outside_the_grammar(key: str) -> None:
    with pytest.raises(PriorityError, match="not a structured field key"):
        build_priority(extensions={key: 1})


def test_the_writer_takes_the_whole_integer_range_and_nothing_more() -> None:
    limit = 999_999_999_999_999
    assert build_priority(extensions={"a": -limit, "b": limit}) == f"a=-{limit}, b={limit}"
    for value in (-limit - 1, limit + 1):
        with pytest.raises(PriorityError, match="outside the Integer range"):
            build_priority(extensions={"a": value})


def test_the_writer_takes_the_whole_date_range_and_nothing_more() -> None:
    limit = 999_999_999_999_999
    built = build_priority(extensions={"a": Date(-limit), "b": Date(limit)})
    assert built == f"a=@-{limit}, b=@{limit}"
    for value in (-limit - 1, limit + 1, 10**16):
        with pytest.raises(PriorityError, match="outside the Integer range"):
            build_priority(extensions={"a": Date(value)})
        with pytest.raises(PriorityError, match="outside the Integer range"):
            PriorityParams(extensions={"a": (Date(value),)})


def test_a_repeated_key_keeps_its_first_place_and_its_last_value() -> None:
    # Section 4.2.2: a repeated key overwrites the value in place.
    params = parse_params("a=1, b=2, a=3", strict=True)
    assert list(params.extensions.items()) == [("a", 3), ("b", 2)]
    assert build_params(params) == "a=3, b=2"


@pytest.mark.parametrize("char", ["\x7f", "\x1f", "\t", "\x00", "\xe9"])
def test_the_string_writer_refuses_characters_outside_visible_ascii(char: str) -> None:
    for text in (char, "x" + char, "xy" + char + "z"):
        with pytest.raises(PriorityError, match="characters a String cannot carry"):
            PriorityParams(extensions={"a": text})
    assert build_priority(extensions={"a": " ~"}) == 'a=" ~"'


@pytest.mark.parametrize("text", ["a,b", "ab,", "a b", "abc;", "a=b", "a(b"])
def test_the_token_writer_checks_every_character(text: str) -> None:
    with pytest.raises(PriorityError, match="is not a Token"):
        build_priority(extensions={"a": Token(text)})
    assert build_priority(extensions={"a": Token("a:b/c")}) == "a=a:b/c"


def test_h2_decode_keeps_every_payload_octet_as_sent() -> None:
    frame = bytes.fromhex("00000810000000000000000001") + b"u=1\xff"
    update = decode_h2_update(frame)
    assert update.field_value == "u=1\xff"
    with pytest.raises(FrameError) as caught:
        update.priority(strict=True)
    assert (caught.value.code, caught.value.offset) == ("PROTOCOL_ERROR", 3)


def test_h3_decode_keeps_every_payload_octet_as_sent() -> None:
    update = decode_h3_update(bytes.fromhex("800f0700") + bytes([5, 4]) + b"u=1\xff")
    assert update.field_value == "u=1\xff"
    assert update.priority() == Priority()
    with pytest.raises(FrameError) as caught:
        update.priority(strict=True)
    assert (caught.value.code, caught.value.offset) == ("H3_GENERAL_PROTOCOL_ERROR", 3)


def _varint(value: int) -> bytes:
    for prefix, size in ((0, 1), (1, 2), (2, 4), (3, 8)):
        if value < 1 << (8 * size - 2):
            return (value | prefix << (8 * size - 2)).to_bytes(size, "big")
    raise AssertionError(value)


OTHER_TYPES = [0x00, 0x01, 0x04, 0x10, 0x3F, 0x40, 0xF06FF, 0xF0702, 0xF0710, 0x0F0700 << 8]


@pytest.mark.parametrize("kind", OTHER_TYPES, ids=hex)
def test_h3_decode_takes_only_the_two_priority_update_types(kind: int) -> None:
    payload = bytes([4]) + b"u=1"
    with pytest.raises(FrameError, match="not an HTTP/3 PRIORITY_UPDATE frame") as caught:
        decode_h3_update(_varint(kind) + _varint(len(payload)) + payload)
    assert caught.value.code is None
    for kind, target in ((0xF0700, "stream"), (0xF0701, "push")):
        assert decode_h3_update(_varint(kind) + _varint(len(payload)) + payload).target == target
