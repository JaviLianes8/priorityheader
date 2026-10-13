"""Error types for priorityheader."""

from __future__ import annotations


class PriorityError(ValueError):
    """A Priority value that cannot be built, or a field that fails a strict parse.

    ``offset`` is the position in the field value where a strict parse stopped, or None
    when the error is not about a position in a value.
    """

    def __init__(self, message: str, offset: int | None = None) -> None:
        super().__init__(message)
        self.offset = offset


class FrameError(PriorityError):
    """A PRIORITY_UPDATE frame that cannot be encoded or decoded.

    ``code`` names the connection error RFC 9218, RFC 9113 or RFC 9114 assigns to the
    problem (for example ``"PROTOCOL_ERROR"`` or ``"H3_ID_ERROR"``), or is None when the
    bytes are not a single PRIORITY_UPDATE frame at all.
    """

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
