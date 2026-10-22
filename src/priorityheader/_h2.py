"""HTTP/2 PRIORITY_UPDATE frames (RFC 9218 section 7.1, RFC 9113 section 4.1)."""

from __future__ import annotations

from ._errors import FrameError
from ._frames import H2_FRAME_TYPE, PriorityUpdate, check_id, octets, value_octets

#: RFC 9113 section 6.5.2: the initial SETTINGS_MAX_FRAME_SIZE.
H2_DEFAULT_MAX_FRAME_SIZE = 16384
_H2_MAX_FRAME_SIZE = (1 << 24) - 1
_STREAM_MASK = (1 << 31) - 1


def encode_h2_update(
    stream_id: int, field_value: str, *, max_frame_size: int = H2_DEFAULT_MAX_FRAME_SIZE
) -> bytes:
    """Encode an HTTP/2 PRIORITY_UPDATE frame, header included, for stream ``stream_id``.

    ``stream_id`` is 1..2**31-1 and ``field_value`` must parse as a structured field
    Dictionary; ``max_frame_size`` is the peer's SETTINGS_MAX_FRAME_SIZE (16384 to
    2**24-1). Raises FrameError for a number out of range, a value that does not parse or a
    payload larger than the limit, and TypeError for a wrong type.

    >>> from priorityheader import encode_h2_update
    >>> encode_h2_update(5, "u=0").hex()
    '00000710000000000000000005753d30'
    """
    stream = check_id(stream_id, 1, _STREAM_MASK, "stream_id")
    payload = stream.to_bytes(4, "big") + value_octets(field_value)
    limit = check_id(
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
    The reserved bits and the flags are ignored, as RFC 9113 section 4.1 requires. Bytes
    that are not exactly one PRIORITY_UPDATE frame raise FrameError with ``code`` None.

    >>> from priorityheader import decode_h2_update
    >>> decode_h2_update(bytes.fromhex("00000710000000000000000005753d30"))
    PriorityUpdate(element_id=5, field_value='u=0', target='stream', protocol='h2')
    """
    data = octets(frame)
    check_id(max_frame_size, H2_DEFAULT_MAX_FRAME_SIZE, _H2_MAX_FRAME_SIZE, "max_frame_size")
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
    return PriorityUpdate(element, data[13:].decode("latin-1"), "stream", "h2")
