"""PRIORITY_UPDATE frames for HTTP/2 (RFC 9218 section 7.1) and HTTP/3 (section 7.2)."""

from __future__ import annotations

from typing import Literal, NamedTuple

from ._errors import FrameError, PriorityError
from ._model import Priority
from ._parse import parse_priority
from ._sfdict import parse_dictionary

H2_FRAME_TYPE = 0x10
H3_REQUEST_FRAME_TYPE = 0xF0700
H3_PUSH_FRAME_TYPE = 0xF0701
#: RFC 9113 section 6.5.2: the initial SETTINGS_MAX_FRAME_SIZE.
H2_DEFAULT_MAX_FRAME_SIZE = 16384
_H2_MAX_FRAME_SIZE = (1 << 24) - 1
_STREAM_MASK = (1 << 31) - 1
VARINT_MAX = (1 << 62) - 1

Target = Literal["stream", "push"]


class PriorityUpdate(NamedTuple):
    """A decoded PRIORITY_UPDATE frame.

    ``element_id`` is the prioritized stream ID, or the push ID when ``target`` is
    ``"push"`` (HTTP/3 type 0xF0701). ``field_value`` is the Priority Field Value as sent.
    """

    element_id: int
    field_value: str
    target: Target = "stream"

    def priority(self, *, strict: bool = False) -> Priority:
        """The priority the frame asks for; absent members take their defaults (section 7).

        With ``strict`` a value that fails to parse raises PriorityError, which RFC 9218
        allows a receiver to treat as a connection error.
        """
        return parse_priority(self.field_value, strict=strict)


def _value_octets(field_value: str) -> bytes:
    if not isinstance(field_value, str):
        raise TypeError(f"field_value must be a str, got {field_value!r}")
    try:
        parse_dictionary(field_value)
    except PriorityError as error:
        raise FrameError(f"the Priority Field Value does not parse: {error}") from None
    return field_value.encode("ascii")


def _octets(frame: object) -> bytes:
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise TypeError(f"a frame is bytes, got {frame!r}")
    return bytes(frame)


def _check_id(value: object, low: int, high: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{what} must be an int, got {value!r}")
    if not low <= value <= high:
        raise FrameError(f"{what} {value} is outside {low}..{high}")
    return value


def encode_h2_update(
    stream_id: int, field_value: str, *, max_frame_size: int = H2_DEFAULT_MAX_FRAME_SIZE
) -> bytes:
    """Encode an HTTP/2 PRIORITY_UPDATE frame, header included, for stream ``stream_id``."""
    _check_id(stream_id, 1, _STREAM_MASK, "stream_id")
    payload = stream_id.to_bytes(4, "big") + _value_octets(field_value)
    limit = _check_id(
        max_frame_size, H2_DEFAULT_MAX_FRAME_SIZE, _H2_MAX_FRAME_SIZE, "max_frame_size"
    )
    if len(payload) > limit:
        raise FrameError(f"a {len(payload)} byte payload exceeds the {limit} byte frame size")
    # Flags 0 and the frame's own Stream Identifier 0: the frame belongs to the connection.
    return len(payload).to_bytes(3, "big") + bytes([H2_FRAME_TYPE, 0]) + bytes(4) + payload


def decode_h2_update(
    frame: bytes | bytearray | memoryview, *, max_frame_size: int = H2_DEFAULT_MAX_FRAME_SIZE
) -> PriorityUpdate:
    """Decode one complete HTTP/2 PRIORITY_UPDATE frame, header included.

    Raises FrameError with ``code`` set to the connection error RFC 9218 and RFC 9113 name:
    PROTOCOL_ERROR for a non-zero frame Stream Identifier or a zero prioritized stream ID,
    FRAME_SIZE_ERROR for a payload shorter than 4 bytes or larger than ``max_frame_size``.
    The reserved bits are ignored, as RFC 9113 section 4.1 requires.
    """
    data = _octets(frame)
    _check_id(max_frame_size, H2_DEFAULT_MAX_FRAME_SIZE, _H2_MAX_FRAME_SIZE, "max_frame_size")
    if len(data) < 9 or data[3] != H2_FRAME_TYPE:
        raise FrameError("not an HTTP/2 PRIORITY_UPDATE frame")
    length = int.from_bytes(data[:3], "big")
    if len(data) != 9 + length:
        raise FrameError(f"the header announces {length} payload bytes, {len(data) - 9} given")
    if length > max_frame_size:
        raise FrameError(f"{length} bytes exceed the frame size limit", "FRAME_SIZE_ERROR")
    if int.from_bytes(data[5:9], "big") & _STREAM_MASK:
        raise FrameError("PRIORITY_UPDATE must be sent on stream 0", "PROTOCOL_ERROR")
    if length < 4:
        raise FrameError("the payload is too short for a stream ID", "FRAME_SIZE_ERROR")
    element = int.from_bytes(data[9:13], "big") & _STREAM_MASK
    if element == 0:
        raise FrameError("the prioritized stream ID is 0", "PROTOCOL_ERROR")
    return PriorityUpdate(element, data[13:].decode("latin-1"))


def encode_varint(value: int) -> bytes:
    """Encode ``value`` as a QUIC variable-length integer on the fewest bytes (RFC 9000 s16)."""
    _check_id(value, 0, VARINT_MAX, "a variable-length integer")
    for prefix, size in ((0, 1), (1, 2), (2, 4), (3, 8)):
        if value < 1 << (8 * size - 2):
            return (value | prefix << (8 * size - 2)).to_bytes(size, "big")
    raise AssertionError("unreachable: the range check bounds the value")


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Return the variable-length integer at ``offset`` and the offset after it."""
    if offset >= len(data):
        raise FrameError("a variable-length integer is missing", "H3_FRAME_ERROR")
    size = 1 << (data[offset] >> 6)
    if offset + size > len(data):
        raise FrameError("a variable-length integer is truncated", "H3_FRAME_ERROR")
    value = int.from_bytes(data[offset : offset + size], "big") & ((1 << (8 * size - 2)) - 1)
    return value, offset + size


def encode_h3_update(element_id: int, field_value: str, *, target: Target = "stream") -> bytes:
    """Encode an HTTP/3 PRIORITY_UPDATE frame for a request stream or a push ID."""
    if target not in ("stream", "push"):
        raise ValueError(f"target must be 'stream' or 'push', got {target!r}")
    _check_id(element_id, 0, VARINT_MAX, "element_id")
    if target == "stream" and element_id % 4:
        raise FrameError(f"{element_id} is not a client-initiated bidirectional stream")
    kind = H3_REQUEST_FRAME_TYPE if target == "stream" else H3_PUSH_FRAME_TYPE
    payload = encode_varint(element_id) + _value_octets(field_value)
    return encode_varint(kind) + encode_varint(len(payload)) + payload


def decode_h3_update(frame: bytes | bytearray | memoryview) -> PriorityUpdate:
    """Decode one complete HTTP/3 PRIORITY_UPDATE frame (type, length and payload).

    Raises FrameError with ``code`` H3_FRAME_ERROR for a payload that ends inside the
    element ID, and H3_ID_ERROR when the request variant names a stream that is not a
    client-initiated bidirectional (request) stream. Stream limits and push ID state need
    the connection and are left to the caller.
    """
    data = _octets(frame)
    try:
        kind, offset = decode_varint(data)
        length, offset = decode_varint(data, offset)
    except FrameError:
        raise FrameError("not an HTTP/3 PRIORITY_UPDATE frame") from None
    if kind not in (H3_REQUEST_FRAME_TYPE, H3_PUSH_FRAME_TYPE):
        raise FrameError("not an HTTP/3 PRIORITY_UPDATE frame")
    if len(data) - offset != length:
        raise FrameError(f"the frame announces {length} payload bytes, {len(data) - offset} given")
    element, offset = decode_varint(data, offset)
    if kind == H3_REQUEST_FRAME_TYPE and element % 4:
        raise FrameError(f"{element} is not a request stream", "H3_ID_ERROR")
    target: Target = "stream" if kind == H3_REQUEST_FRAME_TYPE else "push"
    return PriorityUpdate(element, data[offset:].decode("latin-1"), target)
