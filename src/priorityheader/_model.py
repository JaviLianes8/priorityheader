"""The Priority value, the explicit parameters of a field, and the urgency range."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import NamedTuple, cast

from ._errors import PriorityError
from ._sftypes import Date, DisplayString, Token
from ._sfwrite import plain, serialize_key, serialize_member

MIN_URGENCY = 0
MAX_URGENCY = 7
DEFAULT_URGENCY = 3
DEFAULT_INCREMENTAL = False

#: A bare item (bool, int, Decimal, str, bytes, Token, Date, DisplayString) or an inner list.
ExtensionValue = int | Decimal | str | bytes | tuple[int | Decimal | str | bytes, ...]


class Priority(NamedTuple):
    """An HTTP Priority signal: an urgency 0..7 (0 is the most urgent) and an incremental flag."""

    urgency: int = DEFAULT_URGENCY
    incremental: bool = DEFAULT_INCREMENTAL


def check_urgency(urgency: object) -> int:
    if isinstance(urgency, bool) or not isinstance(urgency, int):
        raise TypeError(f"urgency must be an int, got {urgency!r}")
    value = int.__int__(urgency)
    if not MIN_URGENCY <= value <= MAX_URGENCY:
        raise PriorityError(f"urgency {value} is outside 0..7")
    return value


def check_incremental(incremental: object) -> bool:
    if not isinstance(incremental, bool):
        raise TypeError(f"incremental must be a bool, got {incremental!r}")
    return incremental


def check_extensions(extensions: object) -> dict[str, ExtensionValue]:
    if not isinstance(extensions, Mapping):
        raise TypeError(f"extensions must be a mapping, got {extensions!r}")
    checked: dict[str, ExtensionValue] = {}
    for key, value in extensions.items():
        name = serialize_key(key)
        if name in ("u", "i"):
            raise PriorityError(f"{name!r} is not an extension; pass it as urgency or incremental")
        value = plain(value)
        # Serializing proves the value is representable, so building can never fail later.
        serialize_member(value)
        for item in value if isinstance(value, tuple) else (value,):
            if isinstance(item, Decimal) and item != item.quantize(Decimal("0.001")):
                raise PriorityError(f"{item} has more than three decimal places")
        checked[name] = cast(ExtensionValue, value)
    return checked


class PriorityParams:
    """The priority parameters a field carries, with None for a member that is absent.

    A request treats an absent member as its default; a response treats it as "keep the
    client value" (RFC 9218 section 8). ``extensions`` holds the members other than ``u``
    and ``i`` (section 4.3), by key, in field order; their parameters are not kept.
    Instances are immutable, hashable and compare by value.
    """

    __slots__ = ("_extensions", "_incremental", "_urgency")

    def __init__(
        self,
        urgency: int | None = None,
        incremental: bool | None = None,
        extensions: Mapping[str, ExtensionValue] | None = None,
    ) -> None:
        self._urgency = None if urgency is None else check_urgency(urgency)
        self._incremental = None if incremental is None else check_incremental(incremental)
        self._extensions = MappingProxyType(check_extensions(extensions or {}))

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
        """Return ``base`` with every member present here replacing the one in ``base``."""
        return Priority(
            base.urgency if self._urgency is None else self._urgency,
            base.incremental if self._incremental is None else self._incremental,
        )

    def resolve(self) -> Priority:
        """Apply the defaults to absent members, as a request or PRIORITY_UPDATE reader does."""
        return self.over(Priority())

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
