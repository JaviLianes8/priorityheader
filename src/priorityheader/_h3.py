"""HTTP/3 PRIORITY_UPDATE frames (RFC 9218 section 7.2) and QUIC variable-length integers."""

from __future__ import annotations

from ._errors import FrameError, shown
from ._frames import (
    H3_PUSH_FRAME_TYPE,
    H3_REQUEST_FRAME_TYPE,
    PriorityUpdate,
    Target,
    check_id,
    octets,
    value_octets,
)

VARINT_MAX = (1 << 62) - 1


def encode_varint(value: int) -> bytes:
    """Encode ``value`` as a QUIC variable-length integer on the fewest bytes (RFC 9000 s16)."""
    number = check_id(value, 0, VARINT_MAX, "a variable-length integer")
    for prefix, size in ((0, 1), (1, 2), (2, 4), (3, 8)):
        if number < 1 << (8 * size - 2):
            return (number | prefix << (8 * size - 2)).to_bytes(size, "big")
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
    """Encode an HTTP/3 PRIORITY_UPDATE frame for a request stream or a push ID.

    ``target`` is ``"stream"`` (type 0xF0700, ``element_id`` a client-initiated
    bidirectional stream ID, so a multiple of 4) or ``"push"`` (type 0xF0701, a push ID).
    Raises FrameError for an unknown target name, an ID out of range or of the wrong kind,
    or a value that does not parse, and TypeError for a wrong type (a ``target`` that is not
    a str included).

    >>> from priorityheader import encode_h3_update
    >>> encode_h3_update(4, "u=1").hex()
    '800f07000404753d31'
    """
    if not isinstance(target, str):
        raise TypeError(f"target must be a str, got {shown(target)}")
    if str.__str__(target) not in ("stream", "push"):
        raise FrameError(f"target must be 'stream' or 'push', got {shown(target)}")
    target = "stream" if str.__str__(target) == "stream" else "push"
    element = check_id(element_id, 0, VARINT_MAX, "element_id")
    if target == "stream" and element % 4:
        raise FrameError(f"{element} is not a client-initiated bidirectional stream")
    kind = H3_REQUEST_FRAME_TYPE if target == "stream" else H3_PUSH_FRAME_TYPE
    payload = encode_varint(element) + value_octets(field_value)
    return encode_varint(kind) + encode_varint(len(payload)) + payload


def decode_h3_update(frame: bytes | bytearray | memoryview) -> PriorityUpdate:
    """Decode one complete HTTP/3 PRIORITY_UPDATE frame (type, length and payload).

    Raises FrameError with ``code`` H3_FRAME_ERROR for a payload that ends inside the
    element ID, and H3_ID_ERROR when the request variant names a stream that is not a
    client-initiated bidirectional (request) stream. Bytes that are not exactly one
    PRIORITY_UPDATE frame raise FrameError with ``code`` None. Stream limits and push ID
    state need the connection and are left to the caller.

    >>> from priorityheader import decode_h3_update
    >>> decode_h3_update(bytes.fromhex("800f0701 04 03 753d36")).priority()
    Priority(urgency=6, incremental=False)
    """
    data = octets(frame)
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
    return PriorityUpdate(element, data[offset:].decode("latin-1"), target, "h3")
