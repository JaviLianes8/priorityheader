"""The Priority value, the explicit parameters of a field, and the urgency range."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import Any, NamedTuple, TypeVar, cast

from ._errors import PriorityError, shown
from ._sftypes import Date, DisplayString, Token
from ._sfwrite import plain, serialize_key, serialize_member, to_three_places

MIN_URGENCY = 0
MAX_URGENCY = 7
DEFAULT_URGENCY = 3
DEFAULT_INCREMENTAL = False

#: A bare item (bool, int, Decimal, str, bytes, Token, Date, DisplayString) or an inner list.
ExtensionValue = int | Decimal | str | bytes | tuple[int | Decimal | str | bytes, ...]


def check_urgency(urgency: object) -> int:
    if isinstance(urgency, bool) or not isinstance(urgency, int):
        raise TypeError(f"urgency must be an int, got {shown(urgency)}")
    value = int.__int__(urgency)
    if not MIN_URGENCY <= value <= MAX_URGENCY:
        raise PriorityError(f"urgency {shown(value)} is outside 0..7")
    return value


def check_incremental(incremental: object) -> bool:
    if not isinstance(incremental, bool):
        raise TypeError(f"incremental must be a bool, got {shown(incremental)}")
    return incremental


_P = TypeVar("_P", bound="Priority")


class _PriorityFields(NamedTuple):
    urgency: int = DEFAULT_URGENCY
    incremental: bool = DEFAULT_INCREMENTAL


class Priority(_PriorityFields):
    """An HTTP Priority signal: an urgency 0..7 (0 is the most urgent) and an incremental flag.

    A named tuple whose fields are checked on construction: PriorityError for an urgency
    outside 0..7, TypeError for an urgency that is not an int or a flag that is not a bool.

    >>> from priorityheader import Priority
    >>> Priority()
    Priority(urgency=3, incremental=False)
    >>> urgency, incremental = Priority(1, True)
    >>> urgency, incremental
    (1, True)
    >>> Priority(1)._replace(incremental=True)
    Priority(urgency=1, incremental=True)
    """

    __slots__ = ()
    __module__ = "priorityheader"

    def __new__(
        cls, urgency: int = DEFAULT_URGENCY, incremental: bool = DEFAULT_INCREMENTAL
    ) -> Priority:
        return super().__new__(cls, check_urgency(urgency), check_incremental(incremental))

    @classmethod
    def _make(cls: type[_P], iterable: Iterable[Any]) -> _P:  # type: ignore[override]
        # The tuple default skips __new__; going through it keeps _replace checked too.
        return cls(*iterable)


def check_extensions(extensions: object) -> dict[str, ExtensionValue]:
    if not isinstance(extensions, Mapping):
        raise TypeError(f"extensions must be a mapping, got {shown(extensions)}")
    checked: dict[str, ExtensionValue] = {}
    for key, value in extensions.items():
        name = serialize_key(key)
        if name in ("u", "i"):
            raise PriorityError(f"{name!r} is not an extension; pass it as urgency or incremental")
        value = plain(value)
        # Serializing proves the value is representable, so building can never fail later.
        serialize_member(value)
        for item in value if isinstance(value, tuple) else (value,):
            if isinstance(item, Decimal) and item != to_three_places(item):
                raise PriorityError(f"{shown(item)} has more than three decimal places")
        checked[name] = cast(ExtensionValue, value)
    return checked


class PriorityParams:
    """The priority parameters a field carries, with None for a member that is absent.

    A request treats an absent member as its default; a response treats it as "keep the
    client value" (RFC 9218 section 8). ``extensions`` holds the members other than ``u``
    and ``i`` (section 4.3), by key, in field order; their parameters are not kept.
    Instances are immutable, hashable, compare by value and can be pickled and copied.
    PriorityError or TypeError is raised for a member that could not be written back.

    >>> from priorityheader import Priority, PriorityParams, Token
    >>> params = PriorityParams(urgency=1, extensions={"hint": Token("viewport")})
    >>> params.urgency, params.incremental, dict(params.extensions)
    (1, None, {'hint': Token('viewport')})
    >>> params.over(Priority(5, True))
    Priority(urgency=1, incremental=True)
    >>> params.resolve()
    Priority(urgency=1, incremental=False)
    """

    __slots__ = ("_extensions", "_incremental", "_urgency")
    __module__ = "priorityheader"

    def __init__(
        self,
        urgency: int | None = None,
        incremental: bool | None = None,
        extensions: Mapping[str, ExtensionValue] | None = None,
    ) -> None:
        self._urgency = None if urgency is None else check_urgency(urgency)
        self._incremental = None if incremental is None else check_incremental(incremental)
        self._extensions = MappingProxyType(
            check_extensions({} if extensions is None else extensions)
        )

    @property
    def urgency(self) -> int | None:
        """The urgency member, or None when it is absent."""
        return self._urgency

    @property
    def incremental(self) -> bool | None:
        """The incremental member, or None when it is absent."""
        return self._incremental

    @property
    def extensions(self) -> Mapping[str, ExtensionValue]:
        """Members other than ``u`` and ``i``, read-only."""
        return self._extensions

    def over(self, base: Priority) -> Priority:
        """Return ``base`` with every member present here replacing the one in ``base``.

        TypeError when ``base`` is not a Priority.
        """
        if not isinstance(base, Priority):
            raise TypeError(f"base must be a Priority, got {shown(base)}")
        return Priority(
            base.urgency if self._urgency is None else self._urgency,
            base.incremental if self._incremental is None else self._incremental,
        )

    def resolve(self) -> Priority:
        """Apply the defaults to absent members, as a request or PRIORITY_UPDATE reader does."""
        return self.over(Priority())

    def __reduce__(self) -> tuple[type[PriorityParams], tuple[object, ...]]:
        return (PriorityParams, (self._urgency, self._incremental, dict(self._extensions)))

    def _key(self) -> tuple[object, ...]:
        # Tagging by type keeps True apart from 1 and a Token apart from a String, which
        # Python would otherwise treat as equal although they serialize differently.
        tagged = frozenset((key, _tag(value)) for key, value in self._extensions.items())
        return (self._urgency, self._incremental, tagged)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriorityParams):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __repr__(self) -> str:
        extra = f", extensions={dict(self._extensions)!r}" if self._extensions else ""
        return (
            f"PriorityParams(urgency={self._urgency!r}, incremental={self._incremental!r}{extra})"
        )


_KINDS = frozenset({Token, DisplayString, Date, bool, int, Decimal, str, bytes})


def _tag(value: object) -> object:
    if isinstance(value, tuple):
        return tuple(_tag(item) for item in value)
    kind = next(kind for kind in type(value).__mro__ if kind in _KINDS)
    return (kind.__name__, value)
