"""HTTP/2 PRIORITY_UPDATE frames and the checks shared by both encoders.

The byte strings here are written by hand from RFC 9218 figure 1 and the RFC 9113 frame
header (https://www.rfc-editor.org/rfc/rfc9218.txt), not copied.
"""

import pytest

from priorityheader import (
    FrameError,
    Priority,
    PriorityError,
    PriorityUpdate,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    encode_h3_update,
)

# Length 7, type 0x10, flags 0, stream 0, prioritized stream 5, then the field value.
H2_U0 = bytes.fromhex("000007 10 00 00000000 00000005") + b"u=0"


def test_h2_encode_writes_the_frame_layout() -> None:
    assert encode_h2_update(5, "u=0") == H2_U0


def test_h2_decode_reads_the_frame() -> None:
    update = decode_h2_update(H2_U0)
    assert update == PriorityUpdate(5, "u=0", "stream", "h2")
    assert update.priority() == Priority(0, False)


def test_h2_decode_accepts_bytearray_and_memoryview() -> None:
    assert decode_h2_update(bytearray(H2_U0)).element_id == 5
    assert decode_h2_update(memoryview(H2_U0)).element_id == 5


def test_h2_decode_ignores_the_reserved_bits_and_the_flags() -> None:
    frame = bytes.fromhex("00000710ff8000000080000005") + b"u=0"
    assert decode_h2_update(frame).element_id == 5


@pytest.mark.parametrize(
    "frame,code",
    [
        (bytes.fromhex("00000410000000000100000005"), "PROTOCOL_ERROR"),
        (bytes.fromhex("00000410000000000080000000"), "PROTOCOL_ERROR"),
        (bytes.fromhex("000003100000000000000005"), "FRAME_SIZE_ERROR"),
        (bytes.fromhex("000000100000000000"), "FRAME_SIZE_ERROR"),
        (bytes.fromhex("00000411000000000000000005"), None),
        (bytes.fromhex("0000041000000000"), None),
        (bytes.fromhex("0000041000000000000000000500"), None),
        (b"", None),
    ],
)
def test_h2_decode_errors_carry_the_rfc_code(frame: bytes, code: str | None) -> None:
    with pytest.raises(FrameError) as caught:
        decode_h2_update(frame)
    assert caught.value.code == code


def test_h2_decode_honours_a_larger_frame_size_setting() -> None:
    frame = encode_h2_update(1, "u=1", max_frame_size=16384)
    big = encode_h2_update(1, ", ".join(f"k{n}" for n in range(4000)), max_frame_size=1 << 20)
    assert decode_h2_update(frame).element_id == 1
    assert decode_h2_update(big, max_frame_size=1 << 20).element_id == 1
    with pytest.raises(FrameError) as caught:
        decode_h2_update(big)
    assert caught.value.code == "FRAME_SIZE_ERROR"


def test_h2_encode_refuses_a_payload_over_the_frame_size() -> None:
    value = ", ".join(f"k{n}" for n in range(4000))
    with pytest.raises(FrameError):
        encode_h2_update(1, value)


@pytest.mark.parametrize("size", [16383, 1 << 24, True])
def test_frame_size_settings_outside_the_rfc_range_are_refused(size: int) -> None:
    with pytest.raises((FrameError, TypeError)):
        encode_h2_update(1, "u=1", max_frame_size=size)
    with pytest.raises((FrameError, TypeError)):
        decode_h2_update(H2_U0, max_frame_size=size)


@pytest.mark.parametrize("stream_id", [0, 1 << 31, -1])
def test_h2_encode_refuses_stream_ids_outside_1_to_2_31(stream_id: int) -> None:
    with pytest.raises(FrameError):
        encode_h2_update(stream_id, "u=1")


def test_h2_encode_accepts_the_largest_stream_id() -> None:
    frame = encode_h2_update((1 << 31) - 1, "")
    assert decode_h2_update(frame) == PriorityUpdate((1 << 31) - 1, "")


def test_encoders_refuse_a_value_that_does_not_parse() -> None:
    for value in ("u=1,", "u=\u00e9", "u=1\r\nx: y"):
        with pytest.raises(FrameError):
            encode_h2_update(1, value)
        with pytest.raises(FrameError):
            encode_h3_update(0, value)


def test_encoders_and_decoders_check_types() -> None:
    with pytest.raises(TypeError):
        encode_h2_update(True, "u=1")
    with pytest.raises(TypeError):
        encode_h2_update(1, b"u=1")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        decode_h2_update("frame")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        decode_h3_update(5)  # type: ignore[arg-type]


def test_frame_error_is_a_priority_error() -> None:
    assert issubclass(FrameError, PriorityError)
    assert FrameError("x").code is None


def test_a_strict_priority_read_reports_a_bad_field_value() -> None:
    update = decode_h3_update(bytes.fromhex("800f07000400") + b"u=,")
    assert update.priority() == Priority()
    with pytest.raises(PriorityError):
        update.priority(strict=True)


def test_h2_encode_allows_a_payload_of_exactly_the_frame_size() -> None:
    fits = encode_h2_update(1, "a" * (16384 - 4))
    assert len(fits) == 9 + 16384
    with pytest.raises(FrameError):
        encode_h2_update(1, "a" * (16384 - 3))


def test_h2_decode_allows_a_payload_of_exactly_the_frame_size() -> None:
    fits = encode_h2_update(1, "a" * (16384 - 4))
    assert decode_h2_update(fits).element_id == 1
    over = encode_h2_update(1, "a" * (16384 - 3), max_frame_size=16385)
    with pytest.raises(FrameError) as caught:
        decode_h2_update(over)
    assert caught.value.code == "FRAME_SIZE_ERROR"
