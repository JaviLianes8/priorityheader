"""HTTP/3 PRIORITY_UPDATE frames and varints. The byte strings here are written by hand from
RFC 9218 figure 2 and RFC 9000 section 16 (https://www.rfc-editor.org/rfc/rfc9218.txt,
https://www.rfc-editor.org/rfc/rfc9000.txt), not copied."""

import pytest

from priorityheader import FrameError, Priority, PriorityUpdate, decode_h3_update, encode_h3_update
from priorityheader._frames import decode_varint, encode_varint

H3_REQUEST = bytes.fromhex("800f0700 07 04") + b"u=1, i"
H3_PUSH = bytes.fromhex("800f0701 04 03") + b"u=1"


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
