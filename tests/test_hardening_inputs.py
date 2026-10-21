"""Contracts for hostile arguments: decimal contexts, deep nesting, odd types, subclasses."""

from __future__ import annotations

import decimal
import sys
from collections.abc import Iterator
from decimal import Decimal

import pytest

from priorityheader import (
    Priority,
    PriorityError,
    PriorityParams,
    build_priority,
    encode_h2_update,
    parse_params,
    parse_priority,
)


@pytest.fixture(params=["low precision", "rounding trapped", "inexact trapped"])
def hostile_context(request: pytest.FixtureRequest) -> Iterator[decimal.Context]:
    with decimal.localcontext() as context:
        if request.param == "low precision":
            context.prec = 6
        else:
            signal = decimal.Rounded if request.param == "rounding trapped" else decimal.Inexact
            context.traps[signal] = True
        yield context


@pytest.mark.usefixtures("hostile_context")
def test_the_caller_decimal_context_changes_nothing() -> None:
    assert parse_priority("u=1, a=1234.5") == Priority(1, False)
    assert parse_params("a=-1234.567", strict=True).extensions == {"a": Decimal("-1234.567")}
    assert build_priority(extensions={"a": Decimal("1234.5")}) == "a=1234.5"
    assert build_priority(extensions={"a": Decimal("999999999999.999")}) == "a=999999999999.999"
    params = PriorityParams(extensions={"a": Decimal("-0.5")})
    assert params.extensions["a"] == Decimal("-0.5")


@pytest.mark.usefixtures("hostile_context")
def test_too_many_decimal_places_stay_a_priority_error_in_any_context() -> None:
    with pytest.raises(PriorityError, match="more than three decimal places"):
        build_priority(extensions={"a": Decimal("0.0001")})


def test_a_negative_decimal_keeps_its_sign_and_zero_reads_as_zero() -> None:
    assert parse_params("a=-0.0, b=-12.5").extensions == {"a": Decimal("0"), "b": Decimal("-12.5")}


def _deep(depth: int) -> list[object]:
    top: list[object] = []
    inner = top
    for _ in range(depth):
        child: list[object] = []
        inner.append(child)
        inner = child
    return top


def test_nesting_beyond_an_inner_list_is_a_type_error_at_any_depth() -> None:
    looped: list[object] = []
    looped.append(looped)
    for value in (_deep(2), _deep(sys.getrecursionlimit() + 100), looped, ((1,),)):
        with pytest.raises(TypeError, match="cannot serialize"):
            build_priority(extensions={"a": value})  # type: ignore[dict-item]
        with pytest.raises(TypeError, match="cannot serialize"):
            PriorityParams(extensions={"a": value})  # type: ignore[dict-item]


@pytest.mark.parametrize("value", [0, "", [], (), False, b"", 0.0])
def test_extensions_that_are_not_a_mapping_are_refused_even_when_empty(value: object) -> None:
    with pytest.raises(TypeError, match="extensions must be a mapping"):
        build_priority(extensions=value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="extensions must be a mapping"):
        PriorityParams(extensions=value)  # type: ignore[arg-type]
    assert build_priority(extensions={}) == build_priority(extensions=None) == ""


@pytest.mark.parametrize("base", [(5, True), "x", None, PriorityParams(1)])
def test_over_takes_only_a_priority(base: object) -> None:
    with pytest.raises(TypeError, match="base must be a Priority"):
        PriorityParams(1).over(base)  # type: ignore[arg-type]
    assert PriorityParams(1).over(Priority(5, True)) == Priority(1, True)


def test_priority_keeps_the_named_tuple_field_defaults() -> None:
    assert Priority._field_defaults == {"urgency": 3, "incremental": False}
    assert Priority() == Priority(3, False)


class _BrokenStr(str):
    def __len__(self) -> int:
        raise RuntimeError("boom")

    def __getitem__(self, index: object) -> str:
        raise RuntimeError("boom")


class _BrokenBytes(bytes):
    def __len__(self) -> int:
        raise RuntimeError("boom")


@pytest.mark.parametrize("value", [_BrokenStr("x"), _BrokenStr("y" * 100), _BrokenBytes(b"z")])
def test_a_subclass_that_breaks_len_still_gets_the_documented_type_error(value: object) -> None:
    with pytest.raises(TypeError, match="urgency must be an int"):
        Priority(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="stream_id must be an int"):
        encode_h2_update(value, "u=1")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="incremental must be a bool"):
        build_priority(1, value)  # type: ignore[arg-type]


def test_a_huge_int_is_described_by_its_bit_count_in_every_message() -> None:
    huge = 1 << 1_500_000
    with pytest.raises(PriorityError, match=r"urgency an int of 1500001 bits is outside 0\.\.7"):
        Priority(huge)
    setter = getattr(sys, "set_int_max_str_digits", None)
    if setter is None:
        return
    old = sys.get_int_max_str_digits()
    setter(0)
    try:
        with pytest.raises(PriorityError, match="an int of 1500001 bits"):
            Priority(huge)
    finally:
        setter(old)
