"""Check the library against RFC 9218, 9113, 9114, 9000 and the IANA HTTP Priority registry.

The files are read from tests/upstream (URL, size and sha256 in MANIFEST.json); the tests
that read them skip until `python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from priorityheader import (
    DEFAULT_URGENCY,
    H2_FRAME_TYPE,
    H3_PUSH_FRAME_TYPE,
    H3_REQUEST_FRAME_TYPE,
    MAX_URGENCY,
    MIN_URGENCY,
    FrameError,
    Priority,
    decode_h2_update,
    decode_h3_update,
    merge_priority,
    parse_priority,
)
from priorityheader._h2 import H2_DEFAULT_MAX_FRAME_SIZE
from priorityheader._h3 import decode_varint, encode_varint


def _section(text: str, start: str, end: str) -> str:
    return text.rsplit(start, 1)[1].split(end, 1)[0]


def _priority_lines(block: str) -> list[str]:
    return re.findall(r"^\s+priority = (.+)$", block, flags=re.MULTILINE)


def test_the_urgency_range_and_default_follow_section_4_1(rfc9218: str) -> None:
    section = _section(rfc9218, "4.1.  Urgency", "4.2.  Incremental")
    span = re.search(r"between (\d+) and (\d+)\s+inclusive", section)
    default = re.search(r"The default is (\d+)\.", section)
    assert span is not None and default is not None
    assert (int(span.group(1)), int(span.group(2))) == (MIN_URGENCY, MAX_URGENCY)
    assert int(default.group(1)) == DEFAULT_URGENCY == Priority().urgency


def test_the_incremental_default_follows_section_4_2(rfc9218: str) -> None:
    section = _section(rfc9218, "4.2.  Incremental", "4.3.  Defining")
    assert "default value of the incremental parameter is false" in " ".join(section.split())
    assert Priority().incremental is False


def test_the_section_4_examples_parse(rfc9218: str) -> None:
    (urgent,) = _priority_lines(_section(rfc9218, "4.1.  Urgency", "4.2.  Incremental"))
    (image,) = _priority_lines(_section(rfc9218, "4.2.  Incremental", "4.3.  Defining"))
    # Expected values from https://www.rfc-editor.org/rfc/rfc9218.txt sections 4.1 and 4.2.
    assert parse_priority(urgent, strict=True) == Priority(0, False)
    assert parse_priority(image, strict=True) == Priority(5, True)


def test_the_section_8_merging_example(rfc9218: str) -> None:
    section = _section(rfc9218, "8.  Merging Client", "9.  Client Scheduling")
    request, response = _priority_lines(section)
    # Expected from https://www.rfc-editor.org/rfc/rfc9218.txt section 8: urgency 5 becomes 1
    # and incremental stays true because the server did not send it.
    assert merge_priority(request, response) == Priority(1, True)


def test_the_frame_types_follow_section_7(rfc9218: str) -> None:
    h2 = re.search(r"PRIORITY_UPDATE frame \(type=0x([0-9A-F]+)\)", rfc9218)
    h3 = re.search(r"\(type=0x([0-9A-F]+) or 0x([0-9A-F]+)\)", rfc9218)
    assert h2 is not None and h3 is not None
    assert int(h2.group(1), 16) == H2_FRAME_TYPE
    flat = " ".join(rfc9218.split())
    assert f"type of 0x{H3_REQUEST_FRAME_TYPE:X} is used for request streams" in flat
    assert f"0x{H3_PUSH_FRAME_TYPE:X} is used for push streams" in flat
    assert {int(h3.group(1), 16), int(h3.group(2), 16)} == {
        H3_REQUEST_FRAME_TYPE,
        H3_PUSH_FRAME_TYPE,
    }


def test_the_registry_holds_exactly_u_and_i(iana_xml: str) -> None:
    namespace = {"r": "http://www.iana.org/assignments"}
    root = ET.fromstring(iana_xml)
    names = [str(node.text) for node in root.iterfind(".//r:record/r:name", namespace)]
    assert sorted(names) == ["i", "u"]


def test_the_h2_frame_size_limits_follow_rfc_9113(rfc9113: str) -> None:
    section = " ".join(
        _section(rfc9113, "SETTINGS_MAX_FRAME_SIZE (0x05):", "SETTINGS_MAX_H").split()
    )
    initial = re.search(r"The initial value is 2\^14 \(([\d,]+)\) octets", section)
    largest = re.search(r"2\^24-1 or ([\d,]+) octets", section)
    assert initial is not None and largest is not None
    assert int(initial.group(1).replace(",", "")) == H2_DEFAULT_MAX_FRAME_SIZE
    assert int(largest.group(1).replace(",", "")) == (1 << 24) - 1


def test_the_varint_samples_of_rfc_9000_appendix_a_1(rfc9000: str) -> None:
    section = " ".join(_section(rfc9000, "A.1.  Sample Variable-Length", "A.2.  Sample").split())
    pattern = r"(?:sequence|byte) 0x([0-9a-f]+) decodes to (?:the decimal value )?([\d,]+)"
    samples = [(bytes.fromhex(h), int(v.replace(",", ""))) for h, v in re.findall(pattern, section)]
    again = re.search(r"\(as does the two-byte sequence 0x([0-9a-f]+)\)", section)
    assert len(samples) == 4 and again is not None
    samples.append((bytes.fromhex(again.group(1)), samples[-1][1]))
    for data, value in samples:
        assert decode_varint(data) == (value, len(data))
    # The first four are written on the fewest bytes, so encoding gives them back.
    for data, value in samples[:4]:
        assert encode_varint(value) == data


def _codes(cases: list[bytes], decode: object) -> set[str | None]:
    found: set[str | None] = set()
    for frame in cases:
        with pytest.raises(FrameError) as caught:
            decode(frame)  # type: ignore[operator]
        found.add(caught.value.code)
    return found


def test_every_error_code_is_one_the_rfcs_define(rfc9113: str, rfc9114: str) -> None:
    h2 = _codes(
        [
            bytes.fromhex("000004100000000001") + bytes(4),
            bytes.fromhex("000002100000000000") + bytes(2),
            bytes.fromhex("000004100000000000") + bytes(4),
        ],
        decode_h2_update,
    )
    h3 = _codes([bytes.fromhex("800f07000140"), bytes.fromhex("800f07000101")], decode_h3_update)
    assert h2 == {"PROTOCOL_ERROR", "FRAME_SIZE_ERROR"}
    assert h3 == {"H3_FRAME_ERROR", "H3_ID_ERROR"}
    for code in h2:
        assert re.search(rf"^\s+{code} \(0x[0-9a-f]+\):", rfc9113, flags=re.MULTILINE), code
    for code in h3:
        assert re.search(rf"^\s+{code} \(0x[0-9a-f]+\):", rfc9114, flags=re.MULTILINE), code


def test_the_value_failure_codes_follow_section_7(rfc9218: str, rfc9114: str) -> None:
    section = " ".join(_section(rfc9218, "7.  The PRIORITY_UPDATE Frame", "7.1.  HTTP/2").split())
    assert "In HTTP/2, the error is of type PROTOCOL_ERROR" in section
    assert "in HTTP/3, the error is of type H3_GENERAL_PROTOCOL_ERROR" in section
    assert re.search(r"^\s+H3_GENERAL_PROTOCOL_ERROR \(0x[0-9a-f]+\):", rfc9114, re.MULTILINE)
    h2 = decode_h2_update(bytes.fromhex("000005 10 00 00000000 00000001") + b",")
    h3 = decode_h3_update(bytes.fromhex("800f0700 02 00") + b",")
    codes = []
    for update in (h2, h3):
        with pytest.raises(FrameError) as caught:
            update.priority(strict=True)
        codes.append(caught.value.code)
    assert codes == ["PROTOCOL_ERROR", "H3_GENERAL_PROTOCOL_ERROR"]
