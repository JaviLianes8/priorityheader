"""Contracts for how error messages quote a value, and for hostile str and bytes subclasses."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from priorityheader import (
    Priority,
    PriorityError,
    PriorityParams,
    build_params,
    build_priority,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    parse_params,
    parse_priority,
)


class _Escape(BaseException):
    """Stands for an exception a caller's subclass raises that no `except Exception` catches."""


class _NoLen(str):
    def __len__(self) -> int:
        raise _Escape("len")


class _NoSlice(str):
    def __getitem__(self, index: object) -> str:
        raise _Escape("slice")


class _NoLenBytes(bytes):
    def __len__(self) -> int:
        raise _Escape("len")

    def __bytes__(self) -> bytes:
        raise _Escape("bytes")


class _NoLenBytearray(bytearray):
    def __len__(self) -> int:
        raise _Escape("len")


class _NoBitLength(int):
    def bit_length(self) -> int:
        raise _Escape("bit_length")


class _LyingStr(str):
    def __len__(self) -> int:
        return 0

    def __getitem__(self, index: object) -> str:
        return _LyingStr(str.__str__(self))


class _LongRepr:
    def __repr__(self) -> str:
        return _LyingStr("SECRET-" + "x" * 100_000)


class _BrokenRepr:
    def __repr__(self) -> str:
        raise RuntimeError("repr")


@pytest.mark.parametrize("cls", [_NoLen, _NoSlice])
def test_the_parsers_read_a_hostile_str_subclass_as_its_plain_text(cls: type[str]) -> None:
    assert parse_priority(cls("u=1, i")) == Priority(1, True)
    assert parse_params(cls("u=1")) == PriorityParams(1)
    assert parse_params([cls("u=2"), cls("i")]) == PriorityParams(2, True)
    with pytest.raises(PriorityError) as caught:
        parse_priority(cls("u=1,"), strict=True)
    assert caught.value.offset == 4


def test_the_parsers_read_a_hostile_bytes_subclass_as_its_plain_octets() -> None:
    assert parse_priority(_NoLenBytes(b"u=1")) == Priority(1)
    assert parse_params(_NoLenBytearray(b"i")) == PriorityParams(None, True)


@pytest.mark.parametrize(
    ("text", "offset"), [("a=@+5", 3), ("a=(@+5)", 4), ("a=1;p=@+5", 7), ("a=@x", 3), ("a=@", 3)]
)
def test_a_date_takes_no_plus_sign_and_needs_a_digit(text: str, offset: int) -> None:
    with pytest.raises(PriorityError, match=f"a number needs a digit at offset {offset}") as caught:
        parse_params(text, strict=True)
    assert caught.value.offset == offset
    assert parse_params(text) == PriorityParams()
    assert parse_params("a=@-5", strict=True).extensions["a"] == -5


def _message(call: Callable[[], object]) -> str:
    with pytest.raises((TypeError, PriorityError)) as caught:
        call()
    return str(caught.value)


@pytest.mark.parametrize(
    ("value", "quoted"),
    [
        ("x" * 100, "'" + "x" * 59 + "..."),
        (b"z" * 100, "b'" + "z" * 58 + "..."),
        (["a" * 100], "['" + "a" * 58 + "..."),
        ({"k": "v" * 100}, "{'k': '" + "v" * 53 + "..."),
    ],
)
def test_a_message_quotes_at_most_sixty_characters(value: object, quoted: str) -> None:
    assert len(quoted) == 63
    assert _message(lambda: Priority(value)) == f"urgency must be an int, got {quoted}"  # type: ignore[arg-type]
    assert _message(lambda: build_params(value)) == f"params must be PriorityParams, got {quoted}"  # type: ignore[arg-type]


@pytest.mark.parametrize("bits", [193, 201, 14_300, 20_001, 50_001])
def test_an_int_above_192_bits_is_described_by_its_bit_count(bits: int) -> None:
    huge = 1 << (bits - 1)
    assert _message(lambda: Priority(huge)) == f"urgency an int of {bits} bits is outside 0..7"
    assert _message(lambda: encode_h2_update(huge, "u=1")).startswith(
        f"stream_id an int of {bits} bits is outside"
    )
    assert _message(lambda: build_priority(extensions={"a": huge})) == (
        f"an int of {bits} bits is outside the Integer range"
    )


def test_an_int_of_192_bits_is_quoted_by_its_digits() -> None:
    value = (1 << 192) - 1
    assert _message(lambda: Priority(value)) == f"urgency {value} is outside 0..7"


@pytest.mark.parametrize(
    ("value", "quoted"),
    [
        (_NoLen("y" * 100), "'" + "y" * 59 + "..."),
        (_NoSlice("y" * 100), "'" + "y" * 59 + "..."),
        (_NoLenBytes(b"z" * 3), "b'zzz'"),
        (_NoLenBytearray(b"w" * 3), "_NoLenBytearray(b'www')"),
    ],
)
def test_a_hostile_str_or_bytes_subclass_is_quoted_as_its_plain_value(
    value: object, quoted: str
) -> None:
    assert _message(lambda: Priority(value)) == f"urgency must be an int, got {quoted}"  # type: ignore[arg-type]


def test_a_hostile_int_subclass_is_described_by_the_bit_count_of_its_plain_value() -> None:
    value = _NoBitLength(1 << 300)
    assert _message(lambda: build_priority(1, value)) == (  # type: ignore[arg-type]
        "incremental must be a bool, got an int of 301 bits"
    )


def test_a_value_whose_repr_fails_is_named_by_its_type() -> None:
    assert _message(lambda: Priority(_BrokenRepr())) == (  # type: ignore[arg-type]
        "urgency must be an int, got a _BrokenRepr value"
    )


@pytest.mark.parametrize(
    "call",
    [
        lambda: Priority(_LongRepr()),  # type: ignore[arg-type]
        lambda: build_priority(_LongRepr()),  # type: ignore[arg-type]
        lambda: encode_h2_update(_LongRepr(), "u=1"),  # type: ignore[arg-type]
        lambda: PriorityParams(1).over(_LongRepr()),  # type: ignore[arg-type]
        lambda: decode_h2_update(_LongRepr()),  # type: ignore[arg-type]
        lambda: decode_h3_update(_LongRepr()),  # type: ignore[arg-type]
    ],
)
def test_a_repr_that_lies_about_its_length_is_still_cut(call: Callable[[], object]) -> None:
    message = _message(call)
    assert message.endswith("got SECRET-" + "x" * 53 + "...")
    assert len(message) < 120
