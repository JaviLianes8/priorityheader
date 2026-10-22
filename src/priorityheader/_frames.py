"""What HTTP/2 and HTTP/3 PRIORITY_UPDATE frames share (RFC 9218 section 7)."""

from __future__ import annotations

from typing import Literal, NamedTuple

from ._errors import FrameError, PriorityError, plain_octets, shown
from ._model import Priority
from ._parse import parse_priority
from ._sfdict import parse_dictionary

H2_FRAME_TYPE = 0x10
H3_REQUEST_FRAME_TYPE = 0xF0700
H3_PUSH_FRAME_TYPE = 0xF0701

Target = Literal["stream", "push"]
Protocol = Literal["h2", "h3"]


class PriorityUpdate(NamedTuple):
    """A decoded PRIORITY_UPDATE frame.

    ``element_id`` is the prioritized stream ID, or the push ID when ``target`` is
    ``"push"`` (HTTP/3 type 0xF0701). ``field_value`` is the Priority Field Value as sent,
    and ``protocol`` is ``"h2"`` or ``"h3"``. It is a plain record: the decoders fill it,
    and building one by hand checks nothing.

    >>> from priorityheader import decode_h3_update, encode_h3_update
    >>> update = decode_h3_update(encode_h3_update(8, "u=2, i"))
    >>> update
    PriorityUpdate(element_id=8, field_value='u=2, i', target='stream', protocol='h3')
    >>> update.priority()
    Priority(urgency=2, incremental=True)
    """

    element_id: int
    field_value: str
    target: Target = "stream"
    protocol: Protocol = "h2"

    def priority(self, *, strict: bool = False) -> Priority:
        """The priority the frame asks for; absent members take their defaults (section 7).

        With ``strict`` a value that fails to parse raises FrameError with the code RFC 9218
        section 7 allows a receiver to close the connection with: PROTOCOL_ERROR for HTTP/2,
        H3_GENERAL_PROTOCOL_ERROR for HTTP/3. ``offset`` says where the value broke.

        >>> from priorityheader import FrameError, PriorityUpdate
        >>> PriorityUpdate(1, "u=1, i=?2").priority()
        Priority(urgency=3, incremental=False)
        >>> try:
        ...     PriorityUpdate(1, "u=1, i=?2").priority(strict=True)
        ... except FrameError as error:
        ...     print(error.code, error.offset)
        PROTOCOL_ERROR 8
        """
        try:
            return parse_priority(self.field_value, strict=strict)
        except PriorityError as error:
            code = "PROTOCOL_ERROR" if self.protocol == "h2" else "H3_GENERAL_PROTOCOL_ERROR"
            message = f"the Priority Field Value does not parse: {error}"
            raise FrameError(message, code, error.offset) from None


def value_octets(field_value: object) -> bytes:
    """Return the octets of a Priority Field Value that parses, for a frame payload."""
    if not isinstance(field_value, str):
        raise TypeError(f"field_value must be a str, got {shown(field_value)}")
    text = str.__str__(field_value)
    try:
        parse_dictionary(text)
    except PriorityError as error:
        message = f"the Priority Field Value does not parse: {error}"
        raise FrameError(message, None, error.offset) from None
    return text.encode("ascii")


def octets(frame: object) -> bytes:
    """Return a copy of the frame bytes, refusing anything that is not bytes-like."""
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise TypeError(f"a frame is bytes, got {shown(frame)}")
    return plain_octets(frame)


def check_id(value: object, low: int, high: int, what: str) -> int:
    """Return ``value`` as a plain int when it is an int in ``low..high``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{what} must be an int, got {shown(value)}")
    number = int.__int__(value)
    if not low <= number <= high:
        raise FrameError(f"{what} {shown(number)} is outside {low}..{high}")
    return number
