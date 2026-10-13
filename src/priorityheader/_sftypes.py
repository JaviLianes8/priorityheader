"""Structured field value types and the character sets of RFC 9651."""

from __future__ import annotations

from decimal import Decimal


class Token(str):
    """A structured field Token, told apart from a String."""


class DisplayString(str):
    """A structured field Display String (Unicode text)."""


class Date(int):
    """A structured field Date, in whole seconds since the Unix epoch."""


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
