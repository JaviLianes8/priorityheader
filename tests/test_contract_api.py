"""The 1.0 promise of every public name: signatures, value types, errors and their messages."""

from __future__ import annotations

import copy
import inspect
import pickle
from collections.abc import Callable
from decimal import Decimal

import pytest

import priorityheader as ph
from priorityheader import (
    Date,
    DisplayString,
    FrameError,
    Priority,
    PriorityError,
    PriorityParams,
    PriorityUpdate,
    Token,
)

# Parameter names, kinds and defaults are part of the promise: callers may pass them by name.
SIGNATURES = {
    "parse_priority": "(header: 'FieldInput', *, strict: 'bool' = False) -> 'Priority'",
    "parse_params": "(header: 'FieldInput', *, strict: 'bool' = False) -> 'PriorityParams'",
    "merge_priority": "(request: 'FieldInput', response: 'FieldInput') -> 'Priority'",
    "build_priority": "(urgency: 'int' = 3, incremental: 'bool' = False, *, "
    "extensions: 'Mapping[str, ExtensionValue] | None' = None) -> 'str'",
    "build_params": "(params: 'PriorityParams') -> 'str'",
    "encode_h2_update": "(stream_id: 'int', field_value: 'str', *, "
    "max_frame_size: 'int' = 16384) -> 'bytes'",
    "decode_h2_update": "(frame: 'bytes | bytearray | memoryview', *, "
    "max_frame_size: 'int' = 16384) -> 'PriorityUpdate'",
    "encode_h3_update": "(element_id: 'int', field_value: 'str', *, "
    "target: 'Target' = 'stream') -> 'bytes'",
    "decode_h3_update": "(frame: 'bytes | bytearray | memoryview') -> 'PriorityUpdate'",
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    assert str(inspect.signature(getattr(ph, name))) == SIGNATURES[name]


def test_constructor_signatures_are_pinned() -> None:
    assert Priority._fields == ("urgency", "incremental")
    assert PriorityUpdate._fields == ("element_id", "field_value", "target", "protocol")
    assert PriorityUpdate._field_defaults == {"target": "stream", "protocol": "h2"}
    params = inspect.signature(PriorityParams).parameters
    assert [(p.name, p.default) for p in params.values()] == [
        ("urgency", None),
        ("incremental", None),
        ("extensions", None),
    ]
    assert list(inspect.signature(FrameError).parameters) == ["message", "code", "offset"]
    assert list(inspect.signature(PriorityError).parameters) == ["message", "offset"]


def test_constants_have_their_rfc_values() -> None:
    assert (ph.MIN_URGENCY, ph.DEFAULT_URGENCY, ph.MAX_URGENCY) == (0, 3, 7)
    assert ph.H2_FRAME_TYPE == 0x10
    assert (ph.H3_REQUEST_FRAME_TYPE, ph.H3_PUSH_FRAME_TYPE) == (0xF0700, 0xF0701)


def test_error_hierarchy() -> None:
    assert issubclass(FrameError, PriorityError) and issubclass(PriorityError, ValueError)
    error = FrameError("x", "PROTOCOL_ERROR", 4)
    assert (str(error), error.code, error.offset) == ("x", "PROTOCOL_ERROR", 4)
    assert (FrameError("x").code, FrameError("x").offset, PriorityError("x").offset) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    "value",
    [
        Priority(1, True),
        PriorityParams(),
        PriorityParams(0, False, {"a": Token("b"), "d": Date(5), "s": DisplayString("é")}),
        PriorityParams(extensions={"x": (1, Decimal("1.5"), b"\x00", "q")}),
        PriorityUpdate(4, "u=1", "stream", "h3"),
        FrameError("bad", "H3_ID_ERROR", 2),
        PriorityError("bad", 7),
    ],
    ids=repr,
)
def test_values_survive_pickle_and_copy(value: object) -> None:
    for clone in (pickle.loads(pickle.dumps(value)), copy.copy(value), copy.deepcopy(value)):
        assert type(clone) is type(value)
        if isinstance(value, Exception):
            assert vars(clone) == vars(value) and str(clone) == str(value)
        else:
            assert clone == value and repr(clone) == repr(value)


def test_structured_field_types_show_their_type() -> None:
    assert repr(Token("a")) == "Token('a')"
    assert repr(DisplayString("é")) == "DisplayString('é')"
    assert repr(Date(-1)) == "Date(-1)"
    assert Token("a") == "a" and Date(5) == 5


@pytest.mark.parametrize(
    "args,error", [((8,), PriorityError), ((-1,), PriorityError), ((True,), TypeError)]
)
def test_priority_checks_its_urgency(args: tuple[object, ...], error: type[Exception]) -> None:
    with pytest.raises(error):
        Priority(*args)  # type: ignore[arg-type]


def test_priority_checks_every_way_of_building_it() -> None:
    with pytest.raises(TypeError):
        Priority(1, 1)  # type: ignore[arg-type]
    with pytest.raises(PriorityError):
        Priority()._replace(urgency=8)
    with pytest.raises(TypeError):
        Priority._make([1, "yes"])
    assert Priority._make([0, True]) == (0, True)
    assert type(Priority(_Seven(7)).urgency) is int


class _Seven(int):
    pass


class _Hostile:
    def __repr__(self) -> str:
        raise RuntimeError("no repr")


HUGE = "x" * 100_000
BIG = 10**5000
CALLS: list[tuple[str, Callable[[], object]]] = [
    ("urgency type", lambda: ph.build_priority(HUGE)),  # type: ignore[arg-type]
    ("urgency range", lambda: ph.build_priority(BIG)),
    ("incremental", lambda: ph.build_priority(1, HUGE)),  # type: ignore[arg-type]
    ("key", lambda: ph.build_priority(extensions={HUGE.upper(): 1})),
    ("integer", lambda: ph.build_priority(extensions={"x": BIG})),
    ("decimal", lambda: ph.build_priority(extensions={"x": Decimal("9" * 5000)})),
    ("string", lambda: ph.build_priority(extensions={"x": HUGE + "\n"})),
    ("token", lambda: ph.build_priority(extensions={"x": Token(HUGE + " ")})),
    ("item type", lambda: ph.build_priority(extensions={"x": _Hostile()})),  # type: ignore[dict-item]
    ("field type", lambda: ph.parse_priority(_Hostile())),  # type: ignore[arg-type]
    ("params type", lambda: ph.build_params(HUGE)),  # type: ignore[arg-type]
    ("h2 id", lambda: ph.encode_h2_update(BIG, "u=1")),
    ("h2 value", lambda: ph.encode_h2_update(1, HUGE)),
    ("h2 size", lambda: ph.encode_h2_update(1, "u=1", max_frame_size=-BIG)),
    ("h3 id", lambda: ph.encode_h3_update(BIG, "u=1")),
    ("h3 target", lambda: ph.encode_h3_update(4, "u=1", target=HUGE)),  # type: ignore[arg-type]
    ("frame type", lambda: ph.decode_h3_update(HUGE)),  # type: ignore[arg-type]
    ("priority", lambda: Priority(BIG)),
]


@pytest.mark.parametrize("what,call", CALLS, ids=[what for what, _ in CALLS])
def test_errors_are_typed_and_messages_stay_short(what: str, call: Callable[[], object]) -> None:
    with pytest.raises((PriorityError, TypeError)) as caught:
        call()
    assert len(str(caught.value)) < 200, what
    assert type(caught.value) in (PriorityError, FrameError, TypeError)


def test_frame_errors_carry_the_offset_of_a_broken_value() -> None:
    with pytest.raises(FrameError) as caught:
        ph.encode_h2_update(1, "u=1,")
    assert (caught.value.code, caught.value.offset) == (None, 4)
    with pytest.raises(FrameError) as caught:
        ph.encode_h3_update(0, "u=1 i")
    assert caught.value.offset == 4
