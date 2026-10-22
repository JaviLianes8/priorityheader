"""Structured field value types and the character sets of RFC 9651."""

from __future__ import annotations

from decimal import Decimal


class Token(str):
    """A structured field Token, told apart from a String.

    It is a ``str``: it compares equal to the same text, but it is written without quotes.
    Whether the text is a valid Token is checked when a value is built.

    >>> from priorityheader import Token, build_priority
    >>> build_priority(extensions={"a": Token("viewport"), "b": "viewport"})
    'a=viewport, b="viewport"'
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return f"Token({str.__repr__(self)})"


class DisplayString(str):
    """A structured field Display String: Unicode text, written percent-encoded.

    >>> from priorityheader import DisplayString, build_priority, parse_params
    >>> build_priority(extensions={"note": DisplayString("café")})
    'note=%"caf%c3%a9"'
    >>> parse_params('note=%"caf%c3%a9"').extensions["note"]
    DisplayString('café')
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return f"DisplayString({str.__repr__(self)})"


class Date(int):
    """A structured field Date, in whole seconds since the Unix epoch.

    >>> from priorityheader import Date, build_priority, parse_params
    >>> build_priority(extensions={"since": Date(1659578233)})
    'since=@1659578233'
    >>> parse_params("since=@1659578233").extensions["since"]
    Date(1659578233)
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return f"Date({int.__repr__(self)})"


BareItem = int | Decimal | str | bytes
Params = dict[str, BareItem]
InnerList = list[tuple[BareItem, Params]]
Member = tuple[BareItem | InnerList, Params]

DIGITS = frozenset("0123456789")
LCALPHA = frozenset("abcdefghijklmnopqrstuvwxyz")
ALPHA = LCALPHA | frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
KEY_CHARS = LCALPHA | DIGITS | frozenset("_-.*")
# RFC 9110 tchar, plus ":" and "/" which RFC 9651 allows inside a Token.
TOKEN_CHARS = ALPHA | DIGITS | frozenset("!#$%&'*+-.^_`|~:/")
