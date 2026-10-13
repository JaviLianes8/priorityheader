from decimal import Decimal

import pytest

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
    parse_params,
    parse_priority,
)


def test_build_omits_both_defaults() -> None:
    assert build_priority() == ""


def test_build_omits_the_default_urgency() -> None:
    assert build_priority(incremental=True) == "i"


def test_build_omits_a_false_incremental_flag() -> None:
    assert build_priority(urgency=1) == "u=1"


def test_build_renders_both_members() -> None:
    assert build_priority(urgency=0, incremental=True) == "u=0, i"


def test_build_renders_the_highest_urgency() -> None:
    assert build_priority(urgency=7) == "u=7"


def test_build_rejects_an_urgency_above_the_range() -> None:
    with pytest.raises(PriorityError):
        build_priority(urgency=8)


def test_build_rejects_an_urgency_below_the_range() -> None:
    with pytest.raises(PriorityError):
        build_priority(urgency=-1)


def test_build_rejects_a_boolean_urgency() -> None:
    with pytest.raises(TypeError):
        build_priority(urgency=True)


def test_build_rejects_a_non_integer_urgency() -> None:
    with pytest.raises(TypeError):
        build_priority(urgency="3")  # type: ignore[arg-type]


def test_build_rejects_a_non_boolean_incremental() -> None:
    with pytest.raises(TypeError):
        build_priority(incremental=1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "urgency,incremental",
    [(3, False), (0, True), (7, False), (2, True), (5, False)],
)
def test_build_then_parse_round_trips(urgency: int, incremental: bool) -> None:
    rendered = build_priority(urgency=urgency, incremental=incremental)
    assert parse_priority(rendered) == (urgency, incremental)


def test_build_appends_extensions_after_u_and_i() -> None:
    assert build_priority(1, True, extensions={"x": 1, "y": True}) == "u=1, i, x=1, y"


def test_build_writes_every_extension_type() -> None:
    extensions = {
        "a": False,
        "b": Decimal("1.50"),
        "c": 'q"\\',
        "d": Token("tok/1"),
        "e": b"hi",
        "f": Date(5),
        "g": DisplayString("\u00e9%"),
        "h": (1, Token("x")),
        "k": (),
    }
    text = build_priority(extensions=extensions)
    assert (
        text == 'a=?0, b=1.5, c="q\\"\\\\", d=tok/1, e=:aGk=:, f=@5, g=%"%c3%a9%25", h=(1 x), k=()'
    )
    assert parse_params(text, strict=True).extensions == extensions


def test_build_rounds_a_decimal_to_three_places_half_even() -> None:
    assert build_priority(extensions={"x": Decimal("0.0005")}) == "x=0.0"
    assert build_priority(extensions={"x": Decimal("0.0015")}) == "x=0.002"
    assert build_priority(extensions={"x": Decimal("-0.0001")}) == "x=0.0"
    assert build_priority(extensions={"x": Decimal("-2")}) == "x=-2.0"


@pytest.mark.parametrize(
    "extensions",
    [{"u": 1}, {"i": True}, {"Bad": 1}, {"x": "line\r\nX-Injected: 1"}, {"x": "\u00e9"}],
)
def test_build_refuses_unsafe_extensions(extensions: dict[str, ExtensionValue]) -> None:
    with pytest.raises(PriorityError):
        build_priority(extensions=extensions)


def test_build_params_keeps_explicit_defaults() -> None:
    assert build_params(PriorityParams(3, False)) == "u=3, i=?0"
    assert build_params(PriorityParams(incremental=True)) == "i"
    assert build_params(PriorityParams()) == ""


def test_build_params_writes_extensions() -> None:
    assert build_params(PriorityParams(0, None, {"v": Token("a")})) == "u=0, v=a"


def test_build_params_checks_its_argument() -> None:
    with pytest.raises(TypeError):
        build_params("u=1")  # type: ignore[arg-type]


def test_build_params_then_parse_params_round_trips() -> None:
    for params in (
        PriorityParams(),
        PriorityParams(3, False),
        PriorityParams(0, True, {"x": (b"", Decimal("-1.25"))}),
        PriorityParams(None, False, {"*k": Token("*")}),
    ):
        assert parse_params(build_params(params), strict=True) == params


def test_the_build_output_is_what_an_incoming_header_would_carry() -> None:
    # A request with the defaults sends nothing, and reading nothing gives the defaults.
    assert parse_priority(build_priority()) == Priority()
