"""Writer and command line cases added after the second mutation run."""

from __future__ import annotations

import io
import sys
from decimal import Decimal

import pytest

from priorityheader import Date, PriorityError, build_priority
from priorityheader._cli import main
from priorityheader._sfwrite import serialize_bare_item, serialize_key


def test_a_decimal_that_rounds_up_to_thirteen_digits_is_refused() -> None:
    with pytest.raises(PriorityError):
        serialize_bare_item(Decimal("999999999999.9995"))
    assert serialize_bare_item(Decimal("999999999999.9994")) == "999999999999.999"


class _LyingKey(str):
    def __str__(self) -> str:
        return "k\r\nX: y"

    def __format__(self, spec: str) -> str:
        return "k\r\nX: y"


class _LyingDate(Date):
    def __int__(self) -> int:
        return 10**20


class _LyingInt(int):
    def __str__(self) -> str:
        return "1\r\nX: y"

    __repr__ = __str__


def test_a_key_subclass_is_written_as_its_plain_text() -> None:
    assert serialize_key(_LyingKey("k")) == "k" and type(serialize_key(_LyingKey("k"))) is str
    assert build_priority(extensions={_LyingKey("k"): 1}) == "k=1"


def test_a_date_subclass_is_written_from_its_real_value() -> None:
    assert build_priority(extensions={"d": _LyingDate(5)}) == "d=@5"


def test_the_item_writer_takes_plain_values_on_its_own() -> None:
    assert serialize_bare_item(_LyingInt(1)) == "1"


def test_a_head_without_a_priority_field_is_not_read_as_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(b"HTTP/2 200\r\nserver: x\r\n\r\n"))
    try:
        code = main(["--strict"])
    finally:
        sys.stdin = saved
    assert code == 0
    assert '"urgency": 3' in capsys.readouterr().out
