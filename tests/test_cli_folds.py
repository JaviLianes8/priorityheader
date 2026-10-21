"""Edges of the obs-fold in a message head on standard input (RFC 9112 section 5.2)."""

from __future__ import annotations

import gc
import io
import json
import sys
import time
from collections.abc import Callable

import pytest

from priorityheader._cli import _field_lines, main

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


# Octets that Python counts as whitespace but HTTP does not: none of them starts a fold.
NOT_OWS = [b"\r", b"\x0b", b"\x0c", b"\x1c", b"\x1f", b"\x85", b"\xa0"]


@pytest.mark.parametrize("octet", NOT_OWS, ids=lambda octet: octet.hex())
def test_only_a_space_or_a_tab_starts_a_fold(
    octet: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # Joined, ", i" would make the value "u=1 , i"; as a line of its own it is no field line.
    body = HEAD + b"priority: u=1\r\n" + octet + b", i\r\n\r\n"
    code, out, _ = _run(["--strict"], capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert (report["urgency"], report["incremental"], report["canonical"]) == (1, False, "u=1")


@pytest.mark.parametrize("octet", [b"\x0b", b"\x0c", b"\x85"], ids=lambda octet: octet.hex())
@pytest.mark.parametrize(
    ("lines", "offset"),
    [
        (b"priority: u=1{}\r\n , i\r\n", 3),
        (b"priority: u=1\r\n {}, i\r\n", 4),
        (b"priority: u=1\r\n , i{}\r\n", 7),
    ],
    ids=["end-of-folded-line", "start-of-continuation", "end-of-continuation"],
)
def test_a_fold_trims_only_spaces_and_tabs(
    octet: bytes, lines: bytes, offset: int, capsys: pytest.CaptureFixture[str]
) -> None:
    body = HEAD + lines.replace(b"{}", octet) + b"\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    assert (code, out) == (1, ""), body
    assert f"at offset {offset}" in err, (body, err)


@pytest.mark.parametrize("space", [b" ", b"\t", b" \t "], ids=lambda space: space.hex())
def test_whitespace_before_the_line_break_belongs_to_the_fold(
    space: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # obs-fold = OWS CRLF RWS, and the whole of it becomes one SP, also inside a string.
    body = HEAD + b'priority: u=1, x="a' + space + b'\r\n b"\r\n\r\n'
    code, out, _ = _run(["--strict"], capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert report["extensions"] == {"x": '"a b"'}
    assert report["canonical"] == 'u=1, x="a b"'
    code, _, err = _run(["--strict"], capsys, HEAD + b"priority: u=1" + space + b"\r\n i\r\n")
    assert code == 1 and "at offset 4" in err


@pytest.mark.parametrize("blank", [b" ", b"\t", b" \t"], ids=lambda blank: blank.hex())
def test_a_blank_continuation_does_not_end_the_fold(
    blank: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    body = HEAD + b"priority: u=1\r\n" + blank + b"\r\n , i\r\n\r\n"
    code, out, _ = _run(["--strict"], capsys, body)
    assert code == 0 and json.loads(out)["canonical"] == "u=1, i", body
    body = HEAD + b"priority: u=1\r\n" + blank + b"\r\n i\r\n\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    assert (code, out) == (1, "") and "at offset 4" in err, body


@pytest.mark.parametrize(
    "name", [b"priority-hint", b"priorityx", b"xpriority", b"priorities", b"priorit"]
)
def test_only_the_priority_field_name_counts(
    name: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    body = HEAD + name + b": u=1\r\n\r\n"
    code, out, _ = _run(["--strict"], capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert (report["urgency"], report["incremental"], report["canonical"]) == (3, False, "")


def _best_seconds(*calls: Callable[[], object]) -> list[float]:
    # CPU time per call, best of three samples of at least 0.2 s each, as in test_fuzz.py.
    best = [float("inf")] * len(calls)
    enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(3):
            for index, call in enumerate(calls):
                count, start, spent = 0, time.process_time(), 0.0
                while spent < 0.2:
                    call()
                    count += 1
                    spent = time.process_time() - start
                best[index] = min(best[index], spent / count)
    finally:
        if enabled:
            gc.enable()
    return best


def _head(lines: int, line: str) -> str:
    return "HTTP/1.1 200 OK\r\npriority: u=1\r\n" + (line + "\r\n") * lines


def test_reading_folds_takes_linear_time() -> None:
    small, large, flat = _best_seconds(
        lambda: _field_lines(_head(20_000, " , i=?0")),
        lambda: _field_lines(_head(80_000, " , i=?0")),
        lambda: _field_lines(_head(80_000, "priority: i=?0")),
    )
    # Four times the folds take about four times as long; quadratic growth would be 16.
    assert large < 10 * small
    # And a folded line costs no more than a field line of its own.
    assert large < 3 * flat
