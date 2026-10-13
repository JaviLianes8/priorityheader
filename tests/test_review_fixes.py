"""Regression tests for the findings of the independent review; each failed before its fix."""

from __future__ import annotations

import io
import sys
from decimal import Decimal

import pytest

from priorityheader import (
    DisplayString,
    FrameError,
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
from priorityheader._cli import main


@pytest.mark.parametrize("value", ["1e30", "-1e12", "1e12", "9999999999999.5"])
def test_a_huge_decimal_raises_priority_error(value: str) -> None:
    with pytest.raises(PriorityError):
        build_priority(extensions={"x": Decimal(value)})
    with pytest.raises(PriorityError):
        PriorityParams(extensions={"x": Decimal(value)})


class _LyingInt(int):
    def __str__(self) -> str:
        return "1\r\nX-Injected: yes"

    __repr__ = __str__


class _LyingToken(Token):
    def __str__(self) -> str:
        return "a\r\nX: y"


class _LyingStr(str):
    def replace(self, *args: object, **kwargs: object) -> str:
        return "a\r\nb"


def test_an_int_subclass_cannot_inject_a_header() -> None:
    assert build_priority(_LyingInt(1)) == "u=1"
    assert build_priority(extensions={"x": _LyingInt(5)}) == "x=5"


def test_a_token_subclass_cannot_inject_a_header() -> None:
    assert build_priority(extensions={"x": _LyingToken("a")}) == "x=a"


def test_a_str_subclass_cannot_inject_a_header() -> None:
    assert build_priority(extensions={"x": _LyingStr("a")}) == 'x="a"'


def test_stored_values_are_plain_copies() -> None:
    params = PriorityParams(_LyingInt(2), None, {"x": _LyingInt(5), "y": (_LyingStr("a"),)})
    assert type(params.urgency) is int
    assert type(params.extensions["x"]) is int
    assert params.extensions["y"] == ("a",) and type(params.extensions["y"][0]) is str  # type: ignore[index]


def test_a_decimal_that_would_not_read_back_is_refused() -> None:
    with pytest.raises(PriorityError):
        PriorityParams(extensions={"x": Decimal("1.0004")})
    with pytest.raises(PriorityError):
        build_priority(extensions={"x": (Decimal("0.0001"),)})
    params = PriorityParams(extensions={"x": Decimal("1.5000")})
    assert parse_params(build_params(params)) == params


def test_a_lone_surrogate_in_a_display_string_raises_priority_error() -> None:
    with pytest.raises(PriorityError):
        build_priority(extensions={"x": DisplayString("\ud800")})


def test_a_strict_frame_value_failure_carries_the_connection_error_code() -> None:
    h2 = decode_h2_update(bytes.fromhex("000005 10 00 00000000 00000001") + b",")
    with pytest.raises(FrameError) as caught:
        h2.priority(strict=True)
    assert caught.value.code == "PROTOCOL_ERROR" and caught.value.offset == 0
    h3 = decode_h3_update(bytes.fromhex("800f0700 02 00") + b",")
    with pytest.raises(FrameError) as caught:
        h3.priority(strict=True)
    assert caught.value.code == "H3_GENERAL_PROTOCOL_ERROR"
    assert h3.priority() == h2.priority()


@pytest.mark.parametrize("stdin", [b"u:1\n", b"a:b, u=1\n"])
def test_a_broken_value_on_stdin_is_not_mistaken_for_a_header(
    stdin: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin))
    try:
        code = main(["--strict"])
    finally:
        sys.stdin = saved
    assert code == 1
    out, err = capsys.readouterr()
    assert out == "" and "offset" in err


@pytest.mark.parametrize("text", ['a="\\', 'a=%"%', 'a=%"%a', 'a="x'])
def test_an_offset_never_points_past_the_end(text: str) -> None:
    with pytest.raises(PriorityError) as caught:
        parse_priority(text, strict=True)
    assert caught.value.offset is not None and caught.value.offset <= len(text)
