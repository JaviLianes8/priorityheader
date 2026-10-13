"""PRIORITY_UPDATE frames. The byte strings here are written by hand from the frame layouts
of RFC 9218 figures 1 and 2 (https://www.rfc-editor.org/rfc/rfc9218.txt), not copied."""

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
from priorityheader._frames import decode_varint, encode_varint

H2_U0 = bytes.fromhex("00000710000000000000000005") + b"u=0"
H3_REQUEST = bytes.fromhex("800f07000704") + b"u=1, i"
H3_PUSH = bytes.fromhex("800f07010403") + b"u=1"


def test_h2_encode_writes_the_frame_layout() -> None:
    assert encode_h2_update(5, "u=0") == H2_U0


def test_h2_decode_reads_the_frame() -> None:
    update = decode_h2_update(H2_U0)
    assert update == PriorityUpdate(5, "u=0", "stream")
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


def test_h3_encode_writes_both_variants() -> None:
    assert encode_h3_update(4, "u=1, i") == H3_REQUEST
    assert encode_h3_update(3, "u=1", target="push") == H3_PUSH


def test_h3_decode_reads_both_variants() -> None:
    assert decode_h3_update(H3_REQUEST) == PriorityUpdate(4, "u=1, i", "stream")
    assert decode_h3_update(H3_PUSH) == PriorityUpdate(3, "u=1", "push")
    assert decode_h3_update(H3_REQUEST).priority() == Priority(1, True)


def test_h3_decode_accepts_non_minimal_varints() -> None:
    frame = bytes.fromhex("c0000000000f070040078000000c") + b"u=1"
    assert decode_h3_update(frame) == PriorityUpdate(12, "u=1", "stream")


@pytest.mark.parametrize(
    "frame,code",
    [
        (bytes.fromhex("800f07000105"), "H3_ID_ERROR"),
        (bytes.fromhex("800f07000102"), "H3_ID_ERROR"),
        (bytes.fromhex("800f070000"), "H3_FRAME_ERROR"),
        (bytes.fromhex("800f07000140"), "H3_FRAME_ERROR"),
        (bytes.fromhex("800f07020100"), None),
        (bytes.fromhex("800f07000200"), None),
        (bytes.fromhex("800f0700010000"), None),
        (bytes.fromhex("800f07"), None),
        (b"", None),
    ],
)
def test_h3_decode_errors_carry_the_rfc_code(frame: bytes, code: str | None) -> None:
    with pytest.raises(FrameError) as caught:
        decode_h3_update(frame)
    assert caught.value.code == code


def test_h3_push_ids_may_have_any_value() -> None:
    assert decode_h3_update(encode_h3_update(5, "", target="push")).element_id == 5


def test_h3_encode_refuses_ids_that_are_not_request_streams() -> None:
    for element_id in (1, 2, 3):
        with pytest.raises(FrameError):
            encode_h3_update(element_id, "u=1")


def test_h3_encode_checks_the_target_and_the_range() -> None:
    with pytest.raises(ValueError):
        encode_h3_update(0, "u=1", target="other")  # type: ignore[arg-type]
    with pytest.raises(FrameError):
        encode_h3_update(1 << 62, "u=1", target="push")
    with pytest.raises(FrameError):
        encode_h3_update(-4, "u=1")


@pytest.mark.parametrize(
    "value,size", [(0, 1), (63, 1), (64, 2), (16383, 2), (16384, 4), (2**30 - 1, 4), (2**30, 8)]
)
def test_varints_use_the_fewest_bytes(value: int, size: int) -> None:
    data = encode_varint(value)
    assert len(data) == size
    assert decode_varint(b"\x00" + data, 1) == (value, 1 + size)


def test_the_largest_varint_round_trips() -> None:
    assert decode_varint(encode_varint(2**62 - 1)) == (2**62 - 1, 8)
    with pytest.raises(FrameError):
        encode_varint(2**62)


def test_a_strict_priority_read_reports_a_bad_field_value() -> None:
    update = decode_h3_update(bytes.fromhex("800f07000400") + b"u=,")
    assert update.priority() == Priority()
    with pytest.raises(PriorityError):
        update.priority(strict=True)
