"""Error types for priorityheader, and the bounded way their messages quote a value."""

from __future__ import annotations

#: The longest quotation of a caller's value an error message carries.
QUOTE_LIMIT = 60


class PriorityError(ValueError):
    """A Priority value that cannot be built, or a field that fails a strict parse.

    ``offset`` is the position in the field value where a strict parse stopped, or None
    when the error is not about a position in a value. Messages quote at most 60
    characters of any value they mention.

    >>> from priorityheader import PriorityError, parse_priority
    >>> try:
    ...     parse_priority("u=1,", strict=True)
    ... except PriorityError as error:
    ...     print(error.offset, error)
    4 trailing comma at offset 4
    """

    __module__ = "priorityheader"

    def __init__(self, message: str, offset: int | None = None) -> None:
        super().__init__(message)
        self.offset = offset


class FrameError(PriorityError):
    """A PRIORITY_UPDATE frame that cannot be encoded or decoded.

    ``code`` names the connection error RFC 9218, RFC 9113 or RFC 9114 assigns to the
    problem (for example ``"PROTOCOL_ERROR"`` or ``"H3_ID_ERROR"``), or is None when the
    bytes are not a single PRIORITY_UPDATE frame at all or an argument is out of range.
    ``offset`` is set when the frame carries a value that fails a strict parse.

    >>> from priorityheader import FrameError, decode_h2_update
    >>> try:
    ...     decode_h2_update(bytes.fromhex("000004100000000001") + bytes(4))
    ... except FrameError as error:
    ...     print(error.code)
    PROTOCOL_ERROR
    """

    __module__ = "priorityheader"

    def __init__(self, message: str, code: str | None = None, offset: int | None = None) -> None:
        super().__init__(message, offset)
        self.code = code


def shown(value: object) -> str:
    """Return a short printable quotation of ``value`` for an error message.

    The text never exceeds QUOTE_LIMIT characters plus an ellipsis, and building it cannot
    fail: an int too long for ``repr`` or an object whose ``repr`` raises is described by
    its type instead.
    """
    if isinstance(value, (str, bytes, bytearray)) and len(value) > QUOTE_LIMIT:
        value = value[:QUOTE_LIMIT]
        cut = True
    else:
        cut = False
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 192:
        return f"an int of {value.bit_length()} bits"
    try:
        text = repr(value)
    except Exception:
        return f"a {type(value).__name__} value"
    if cut or len(text) > QUOTE_LIMIT:
        return text[:QUOTE_LIMIT] + "..."
    return text
