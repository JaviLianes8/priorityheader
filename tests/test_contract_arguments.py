"""Contracts for argument types: flags, targets, fake bools and lying PriorityParams subclasses."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from unittest.mock import Mock

import pytest

from priorityheader import (
    FrameError,
    Priority,
    PriorityError,
    PriorityParams,
    PriorityUpdate,
    build_params,
    build_priority,
    encode_h3_update,
    parse_params,
    parse_priority,
)


@pytest.mark.parametrize("target", [None, 5, ["stream"], b"stream", ("push",)])
def test_a_target_that_is_not_a_str_is_a_type_error(target: object) -> None:
    with pytest.raises(TypeError, match="target must be a str"):
        encode_h3_update(4, "u=1", target=target)  # type: ignore[arg-type]


def test_an_unknown_target_name_stays_a_frame_error() -> None:
    with pytest.raises(FrameError, match="target must be 'stream' or 'push'"):
        encode_h3_update(4, "u=1", target="request")  # type: ignore[arg-type]


class _Stream(str):
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


def test_a_target_is_compared_by_its_plain_text() -> None:
    assert encode_h3_update(1, "u=1", target=_Stream("push")).hex().startswith("800f0701")  # type: ignore[arg-type]
    with pytest.raises(FrameError, match="target must be 'stream' or 'push'"):
        encode_h3_update(4, "u=1", target=_Stream("other"))  # type: ignore[arg-type]


STRICT_CALLS: list[Callable[[str, object], object]] = [
    lambda value, strict: parse_priority(value, strict=strict),  # type: ignore[arg-type]
    lambda value, strict: parse_params(value, strict=strict),  # type: ignore[arg-type]
    lambda value, strict: PriorityUpdate(1, value).priority(strict=strict),  # type: ignore[arg-type]
]


@pytest.mark.parametrize("strict", ["no", 1, 0, None, Mock(spec=bool)], ids=repr)
@pytest.mark.parametrize("call", STRICT_CALLS, ids=["parse_priority", "parse_params", "priority"])
def test_strict_must_be_a_bool(call: Callable[[str, object], object], strict: object) -> None:
    for value in ("u=1", "u=1,"):
        with pytest.raises(TypeError, match="strict must be a bool"):
            call(value, strict)


@pytest.mark.parametrize("call", STRICT_CALLS, ids=["parse_priority", "parse_params", "priority"])
def test_strict_takes_both_bools(call: Callable[[str, object], object]) -> None:
    call("u=1,", False)
    with pytest.raises(PriorityError):
        call("u=1,", True)


def test_a_fake_bool_is_refused_as_the_incremental_flag() -> None:
    fake = Mock(spec=bool)
    with pytest.raises(TypeError, match="incremental must be a bool"):
        Priority(1, fake)
    with pytest.raises(TypeError, match="incremental must be a bool"):
        PriorityParams(incremental=fake)
    with pytest.raises(TypeError, match="incremental must be a bool"):
        build_priority(1, fake)


@pytest.mark.parametrize("value", [Mock(spec=bool), (1, Mock(spec=bool))], ids=["bare", "inner"])
def test_a_fake_bool_is_refused_as_an_extension_value(value: object) -> None:
    with pytest.raises(TypeError, match="cannot serialize Mock"):
        PriorityParams(extensions={"a": value})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="cannot serialize Mock"):
        build_priority(extensions={"a": value})  # type: ignore[dict-item]


def test_stored_flags_are_the_bool_singletons() -> None:
    params = PriorityParams(incremental=True, extensions={"a": False, "b": (True,)})
    assert params.incremental is True and params.extensions["a"] is False
    assert params.extensions["b"][0] is True  # type: ignore[index]
    assert hash(params) == hash(PriorityParams(incremental=True, extensions=params.extensions))


class _Lying(PriorityParams):
    __slots__ = ()

    @property
    def urgency(self) -> int | None:
        return 99

    @property
    def incremental(self) -> bool | None:
        return "yes"  # type: ignore[return-value]

    @property
    def extensions(self) -> Mapping[str, object]:  # type: ignore[override]
        return {"u": 5, "i": Decimal("1.23456")}


class _Corrupt(PriorityParams):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__()
        object.__setattr__(self, "_urgency", 99)


class _Unset(PriorityParams):
    __slots__ = ()

    def __init__(self) -> None:
        pass


def test_build_params_writes_what_the_base_instance_holds() -> None:
    assert build_params(_Lying(1, True, {"a": 1})) == "u=1, i, a=1"
    assert build_params(_Lying()) == ""


def test_build_params_rechecks_a_subclass_that_corrupts_its_members() -> None:
    with pytest.raises(PriorityError, match=r"urgency 99 is outside 0..7"):
        build_params(_Corrupt())
    with pytest.raises(TypeError, match="initialised PriorityParams"):
        build_params(_Unset())
