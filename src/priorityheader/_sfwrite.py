"""Structured field serialization, as RFC 9651 section 4.1 describes."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from ._errors import PriorityError
from ._sf import ALPHA, KEY_CHARS, LCALPHA, TOKEN_CHARS, BareItem, Date, DisplayString, Token

INTEGER_LIMIT = 999_999_999_999_999
_DECIMAL_LIMIT = 999_999_999_999


def serialize_key(key: object) -> str:
    """Return ``key`` when it is a valid Dictionary or Parameter key."""
    if not isinstance(key, str):
        raise TypeError(f"a key is a str, got {key!r}")
    if not key or (key[0] not in LCALPHA and key[0] != "*"):
        raise PriorityError(f"{key!r} is not a structured field key")
    if any(char not in KEY_CHARS for char in key):
        raise PriorityError(f"{key!r} is not a structured field key")
    return key


def is_token(value: str) -> bool:
    """True when ``value`` can be written as a structured field Token."""
    if not value or (value[0] not in ALPHA and value[0] != "*"):
        return False
    return all(char in TOKEN_CHARS for char in value[1:])


def _integer(value: int) -> str:
    if not -INTEGER_LIMIT <= value <= INTEGER_LIMIT:
        raise PriorityError(f"{value} is outside the Integer range")
    return str(value)


def _decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise PriorityError(f"{value} is not a finite Decimal")
    rounded = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
    if abs(rounded) > _DECIMAL_LIMIT + Decimal("0.999"):
        raise PriorityError(f"{value} has more than 12 integer digits")
    text = f"{rounded:f}".rstrip("0")
    text = text + "0" if text.endswith(".") else text
    return "0.0" if text in ("-0.0", "0.0") else text


def _string(value: str) -> str:
    if any(not " " <= char <= "~" for char in value):
        raise PriorityError(f"{value!r} holds characters a String cannot carry")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _display(value: str) -> str:
    out: list[str] = []
    for octet in value.encode("utf-8"):
        if octet in (0x25, 0x22) or not 0x20 <= octet <= 0x7E:
            out.append(f"%{octet:02x}")
        else:
            out.append(chr(octet))
    return '%"' + "".join(out) + '"'


def serialize_bare_item(value: object) -> str:
    """Serialize one bare item of any RFC 9651 type."""
    if isinstance(value, bool):
        return "?1" if value else "?0"
    if isinstance(value, Date):
        return "@" + _integer(int(value))
    if isinstance(value, int):
        return _integer(value)
    if isinstance(value, Decimal):
        return _decimal(value)
    if isinstance(value, Token):
        if not is_token(value):
            raise PriorityError(f"{str(value)!r} is not a Token")
        return str(value)
    if isinstance(value, DisplayString):
        return _display(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, bytes):
        return ":" + base64.b64encode(value).decode("ascii") + ":"
    raise TypeError(f"cannot serialize {type(value).__name__} as a structured field item")


def serialize_params(params: Mapping[str, BareItem]) -> str:
    out: list[str] = []
    for key, value in params.items():
        name = serialize_key(key)
        out.append(f";{name}" if value is True else f";{name}={serialize_bare_item(value)}")
    return "".join(out)


def serialize_member(value: object) -> str:
    """Serialize a Dictionary member value: a bare item or an inner list (a tuple or list)."""
    if isinstance(value, (tuple, list)):
        return "(" + " ".join(serialize_bare_item(item) for item in value) + ")"
    return serialize_bare_item(value)


def serialize_dictionary(members: Mapping[str, object] | Sequence[tuple[str, object]]) -> str:
    """Serialize a Dictionary of bare items and inner lists, without member parameters."""
    pairs = members.items() if isinstance(members, Mapping) else members
    out: list[str] = []
    for key, value in pairs:
        name = serialize_key(key)
        out.append(name if value is True else f"{name}={serialize_member(value)}")
    return ", ".join(out)
