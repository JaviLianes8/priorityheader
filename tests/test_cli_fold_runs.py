"""Where a run of folds starts and ends in a message head on standard input (RFC 9112)."""

from __future__ import annotations

import io
import json
import sys

import pytest

from priorityheader._cli import main

HEAD = b"HTTP/1.1 200 OK\r\n"


def _run(args: list[str], capsys: pytest.CaptureFixture[str], stdin: bytes) -> tuple[int, str, str]:
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin))
    try:
        code = main(args)
    finally:
        sys.stdin = saved
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.parametrize("space", [b" ", b"\t", b" \t"], ids=lambda space: space.hex())
def test_whitespace_at_the_end_of_a_middle_continuation_belongs_to_the_next_fold(
    space: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # The OWS before the second line break is part of the second obs-fold: one SP in all.
    body = HEAD + b'priority: u=1, x="a\r\n b' + space + b'\r\n c"\r\n\r\n'
    code, out, _ = _run(["--strict"], capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert report["extensions"] == {"x": '"a b c"'}
    assert report["canonical"] == 'u=1, x="a b c"'
    body = HEAD + b"priority: u=1\r\n , i" + space + b"\r\n x\r\n\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    assert (code, out) == (1, "") and "at offset 8" in err, (body, err)


@pytest.mark.parametrize("args", [["--strict"], []], ids=["strict", "lenient"])
def test_several_priority_lines_are_combined_in_order(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    body = HEAD + b"priority: u=1\r\nserver: x\r\npriority: u=2\r\n\r\n"
    code, out, _ = _run(args, capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert (report["urgency"], report["canonical"]) == (2, "u=2")
    # Combined with ", " in order, a string may even span two field lines.
    body = HEAD + b'priority: x="a\r\npriority: b"\r\n\r\n'
    code, out, _ = _run(args, capsys, body)
    assert code == 0 and json.loads(out)["extensions"] == {"x": '"a, b"'}, body


@pytest.mark.parametrize("octet", [b"\x0b", b"\x0c", b"\x85"], ids=lambda octet: octet.hex())
@pytest.mark.parametrize("lead", [b" ", b"\t"], ids=lambda lead: lead.hex())
def test_a_continuation_with_an_octet_besides_spaces_and_tabs_is_not_blank(
    lead: bytes, octet: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # Only a continuation of spaces and tabs adds nothing; this one adds its octet.
    for tail in (b"", b"\r\n , i"):
        body = HEAD + b"priority: u=1\r\n" + lead + octet + tail + b"\r\n\r\n"
        code, out, err = _run(["--strict"], capsys, body)
        assert (code, out) == (1, "") and "at offset 4" in err, (body, err)


@pytest.mark.parametrize("line", [b"", b"garbage"], ids=["empty", "no-field"])
def test_a_line_that_is_no_field_line_ends_the_fold(
    line: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # What follows such a line continues no field line, however it looks.
    for after in (b" , i", b" priority: u=2", b"\tpriority: u=2"):
        body = HEAD + b"priority: u=1\r\n" + line + b"\r\n" + after + b"\r\n\r\n"
        code, out, _ = _run(["--strict"], capsys, body)
        report = json.loads(out)
        assert code == 0, body
        assert (report["urgency"], report["incremental"], report["canonical"]) == (
            1,
            False,
            "u=1",
        ), body
