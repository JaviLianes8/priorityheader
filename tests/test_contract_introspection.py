"""Contracts for introspection: the type hints and the source of every public name resolve.

Tools such as pydantic, IDEs and documentation generators read them, and 0.2.0 gave them.
"""

from __future__ import annotations

import inspect
import typing
from pathlib import Path
from typing import Literal

import pytest

import priorityheader as ph

PUBLIC = [getattr(ph, name) for name in ph.__all__]
CLASSES = [obj for obj in PUBLIC if inspect.isclass(obj)]
FUNCTIONS = [obj for obj in PUBLIC if inspect.isfunction(obj)]
METHODS: list[object] = [
    ph.PriorityParams.__init__,
    ph.PriorityParams.over,
    ph.PriorityParams.resolve,
    ph.PriorityUpdate.priority,
    *(prop.fget for prop in vars(ph.PriorityParams).values() if isinstance(prop, property)),
]


@pytest.mark.parametrize("obj", [*CLASSES, *FUNCTIONS, *METHODS], ids=lambda obj: obj.__qualname__)
def test_type_hints_resolve_for_every_public_class_function_and_method(obj: object) -> None:
    typing.get_type_hints(obj)


def test_priority_update_fields_resolve_to_their_types() -> None:
    assert typing.get_type_hints(ph.PriorityUpdate) == {
        "element_id": int,
        "field_value": str,
        "target": Literal["stream", "push"],
        "protocol": Literal["h2", "h3"],
    }
    hints = typing.get_type_hints(ph.encode_h3_update)
    assert hints["target"] == Literal["stream", "push"]


@pytest.mark.parametrize("cls", CLASSES, ids=lambda cls: cls.__name__)
def test_the_source_of_every_public_class_is_its_own_definition(cls: type) -> None:
    source = inspect.getsource(cls)
    assert source.startswith((f"class {cls.__name__}(", f"class {cls.__name__}:")), source[:80]
    path = Path(inspect.getsourcefile(cls) or "")
    assert path.parent.name == "priorityheader" and path.name.startswith("_"), path


@pytest.mark.parametrize("cls", CLASSES, ids=lambda cls: cls.__name__)
def test_every_public_class_is_reached_from_the_package(cls: type) -> None:
    assert getattr(ph, cls.__name__) is cls
    assert cls.__module__.startswith("priorityheader._")
