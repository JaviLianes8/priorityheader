"""A tolerant reader for the RFC 8941 structured-field dictionary.

Only the structure the Priority header needs is interpreted (integers and
booleans); strings, tokens, byte sequences, inner lists and parameters are
consumed so they never derail the read of the members that matter.
"""

from __future__ import annotations

_KEY_START = set("abcdefghijklmnopqrstuvwxyz*")
_KEY_REST = _KEY_START | set("0123456789_-.")
_TOKEN_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ*")
_TOKEN_REST = _TOKEN_START | set("0123456789:/!#$%&'*+-.^_`|~")


class _Cursor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    @property
    def done(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def skip_space(self) -> None:
        while self.peek() in (" ", "\t"):
            self.pos += 1


def parse_dictionary(text: str) -> dict[str, object]:
    """Read a structured-field dictionary into a mapping, best effort.

    A repeated key keeps its last value, matching RFC 8941. Anything that does
    not parse stops the read, and the members gathered so far are returned, so a
    malformed tail never discards a clean head.
    """
    cursor = _Cursor(text)
    result: dict[str, object] = {}
    cursor.skip_space()
    while not cursor.done:
        try:
            key = _parse_key(cursor)
            value: object = True
            if cursor.peek() == "=":
                cursor.advance()
                value = _parse_value(cursor)
            _skip_parameters(cursor)
        except (IndexError, ValueError):
            break
        result[key] = value
        cursor.skip_space()
        if cursor.peek() != ",":
            break
        cursor.advance()
        cursor.skip_space()
    return result


def _parse_key(cursor: _Cursor) -> str:
    if cursor.peek() not in _KEY_START:
        raise ValueError("invalid key")
    chars = [cursor.advance()]
    while cursor.peek() in _KEY_REST:
        chars.append(cursor.advance())
    return "".join(chars)


def _parse_value(cursor: _Cursor) -> object:
    if cursor.peek() == "(":
        return _skip_inner_list(cursor)
    return _parse_bare_item(cursor)


def _parse_bare_item(cursor: _Cursor) -> object:
    ch = cursor.peek()
    if ch == "?":
        return _parse_boolean(cursor)
    if ch == "-" or ch.isdigit():
        return _parse_number(cursor)
    if ch == '"':
        return _parse_string(cursor)
    if ch == ":":
        return _parse_byte_sequence(cursor)
    if ch in _TOKEN_START:
        return _parse_token(cursor)
    raise ValueError("unknown item")


def _parse_boolean(cursor: _Cursor) -> bool:
    cursor.advance()
    flag = cursor.advance()
    if flag in ("0", "1"):
        return flag == "1"
    raise ValueError("invalid boolean")


def _parse_number(cursor: _Cursor) -> int | float:
    chars: list[str] = []
    if cursor.peek() == "-":
        chars.append(cursor.advance())
    is_decimal = False
    while True:
        ch = cursor.peek()
        if ch.isdigit():
            chars.append(cursor.advance())
        elif ch == "." and not is_decimal:
            is_decimal = True
            chars.append(cursor.advance())
        else:
            break
    text = "".join(chars)
    if not text or text == "-":
        raise ValueError("invalid number")
    return float(text) if is_decimal else int(text)


def _parse_string(cursor: _Cursor) -> str:
    cursor.advance()
    chars: list[str] = []
    while True:
        ch = cursor.advance()
        if ch == "\\":
            chars.append(cursor.advance())
        elif ch == '"':
            return "".join(chars)
        else:
            chars.append(ch)


def _parse_token(cursor: _Cursor) -> str:
    chars = [cursor.advance()]
    while cursor.peek() in _TOKEN_REST:
        chars.append(cursor.advance())
    return "".join(chars)


def _parse_byte_sequence(cursor: _Cursor) -> str:
    cursor.advance()
    chars: list[str] = []
    while True:
        ch = cursor.advance()
        if ch == ":":
            return "".join(chars)
        chars.append(ch)


def _skip_inner_list(cursor: _Cursor) -> list[object]:
    cursor.advance()
    items: list[object] = []
    cursor.skip_space()
    while cursor.peek() != ")":
        if cursor.done:
            raise ValueError("unterminated inner list")
        items.append(_parse_bare_item(cursor))
        _skip_parameters(cursor)
        cursor.skip_space()
    cursor.advance()
    return items


def _skip_parameters(cursor: _Cursor) -> None:
    while cursor.peek() == ";":
        cursor.advance()
        cursor.skip_space()
        _parse_key(cursor)
        if cursor.peek() == "=":
            cursor.advance()
            _parse_bare_item(cursor)
