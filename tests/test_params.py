from decimal import Decimal
from unittest import mock

import pytest

from priorityheader import (
    Date,
    DisplayString,
    Priority,
    PriorityError,
    PriorityParams,
    Token,
    parse_params,
)


def test_absent_members_are_none() -> None:
    params = parse_params("x=1")
    assert params.urgency is None and params.incremental is None
    assert params.extensions == {"x": 1}


def test_present_defaults_are_kept_apart_from_absent_ones() -> None:
    assert parse_params("u=3, i=?0") == PriorityParams(3, False)
    assert parse_params("u=3, i=?0") != PriorityParams()


def test_ignored_members_read_as_absent() -> None:
    assert parse_params("u=8, i=1") == PriorityParams()


def test_a_field_that_fails_to_parse_gives_no_members() -> None:
    assert parse_params("u=1, x=") == PriorityParams()


def test_extensions_keep_every_item_type_in_field_order() -> None:
    params = parse_params('z=?0, y=1.5, x="s", w=t, v=:aGk=:, s=@1, r=%"%c3%a9", q=(1 a)')
    assert list(params.extensions) == ["z", "y", "x", "w", "v", "s", "r", "q"]
    assert params.extensions["z"] is False
    assert params.extensions["y"] == Decimal("1.5")
    assert params.extensions["x"] == "s" and type(params.extensions["x"]) is str
    assert type(params.extensions["w"]) is Token
    assert params.extensions["v"] == b"hi"
    assert type(params.extensions["s"]) is Date
    assert params.extensions["r"] == DisplayString("\u00e9")
    assert params.extensions["q"] == (1, Token("a"))


def test_extensions_are_read_only() -> None:
    params = PriorityParams(extensions={"x": 1})
    with pytest.raises(TypeError):
        params.extensions["y"] = 2  # type: ignore[index]


def test_the_constructor_copies_the_extensions() -> None:
    source = {"x": 1}
    params = PriorityParams(extensions=source)
    source["y"] = 2
    assert dict(params.extensions) == {"x": 1}


def test_a_list_extension_becomes_a_tuple() -> None:
    assert PriorityParams(extensions={"x": [1, 2]}).extensions["x"] == (1, 2)  # type: ignore[dict-item]


def test_over_replaces_only_present_members() -> None:
    base = Priority(5, True)
    assert PriorityParams().over(base) == base
    assert PriorityParams(urgency=1).over(base) == Priority(1, True)
    assert PriorityParams(incremental=False).over(base) == Priority(5, False)
    assert PriorityParams(0, False).over(base) == Priority(0, False)


def test_resolve_applies_the_defaults() -> None:
    assert PriorityParams().resolve() == Priority(3, False)
    assert PriorityParams(incremental=True).resolve() == Priority(3, True)


def test_params_are_hashable_and_compare_by_value() -> None:
    a = PriorityParams(1, True, {"x": (1, 2), "y": b"z"})
    b = PriorityParams(1, True, {"y": b"z", "x": (1, 2)})
    assert a == b and hash(a) == hash(b)
    assert len({a, b}) == 1
    assert a != PriorityParams(1, True) and a != "u=1"


def test_equality_tells_item_types_apart() -> None:
    assert PriorityParams(extensions={"x": True}) != PriorityParams(extensions={"x": 1})
    assert PriorityParams(extensions={"x": Token("a")}) != PriorityParams(extensions={"x": "a"})
    assert PriorityParams(extensions={"x": Date(1)}) != PriorityParams(extensions={"x": 1})
    assert PriorityParams(extensions={"x": DisplayString("a")}) != PriorityParams(
        extensions={"x": "a"}
    )


def test_repr_shows_the_members() -> None:
    assert repr(PriorityParams(1)) == "PriorityParams(urgency=1, incremental=None)"
    assert "extensions={'x': 1}" in repr(PriorityParams(extensions={"x": 1}))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"urgency": 8}, PriorityError),
        ({"urgency": -1}, PriorityError),
        ({"urgency": True}, TypeError),
        ({"urgency": "1"}, TypeError),
        ({"incremental": 1}, TypeError),
        ({"extensions": {"u": 1}}, PriorityError),
        ({"extensions": {"i": True}}, PriorityError),
        ({"extensions": {"X": 1}}, PriorityError),
        ({"extensions": {"": 1}}, PriorityError),
        ({"extensions": {1: 1}}, TypeError),
        ({"extensions": {"x": "a\r\nb"}}, PriorityError),
        ({"extensions": {"x": 10**15}}, PriorityError),
        ({"extensions": {"x": 1.5}}, TypeError),
        ({"extensions": {"x": None}}, TypeError),
        ({"extensions": {"x": ((1,),)}}, TypeError),
        ({"extensions": {"x": Token("1a")}}, PriorityError),
        ({"extensions": {"x": Decimal("1e12")}}, PriorityError),
        ({"extensions": {"x": Decimal("nan")}}, PriorityError),
        ({"extensions": [("x", 1)]}, TypeError),
    ],
)
def test_the_constructor_validates(kwargs: dict[str, object], error: type[Exception]) -> None:
    with pytest.raises(error):
        PriorityParams(**kwargs)  # type: ignore[arg-type]


def test_a_key_of_the_wrong_type_is_named_in_the_error() -> None:
    with pytest.raises(TypeError, match="a key is a str"):
        PriorityParams(extensions={1: 1})  # type: ignore[dict-item]


def test_equality_tells_item_types_apart_inside_inner_lists() -> None:
    assert PriorityParams(extensions={"x": (True,)}) != PriorityParams(extensions={"x": (1,)})


def test_comparison_with_other_types_defers_to_them() -> None:
    assert PriorityParams() == mock.ANY
