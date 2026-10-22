"""How the command line splits standard input into field lines (RFC 9112 sections 2.2, 5.2)."""

import io
import json
import sys

import pytest

from priorityheader._cli import main


def _run(args: list[str], capsys: pytest.CaptureFixture[str], stdin: bytes) -> tuple[int, str, str]:
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin))
    try:
        code = main(args)
    finally:
        sys.stdin = saved
    out, err = capsys.readouterr()
    return code, out, err


HEAD = b"HTTP/1.1 200 OK\r\n"
FOLDS = [b" ", b"\t", b" \t ", b"\t\t"]


@pytest.mark.parametrize("fold", FOLDS, ids=lambda fold: fold.hex())
def test_a_folded_priority_line_is_one_value(
    fold: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    # An obs-fold is replaced by a single SP before the value is read, so "u=1 i" fails.
    body = HEAD + b"priority: u=1\r\n" + fold + b"i\r\n\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    assert (code, out) == (1, ""), body
    assert "offset 4" in err
    code, out, _ = _run([], capsys, body)
    report = json.loads(out)
    assert code == 0 and (report["urgency"], report["incremental"]) == (3, False)


def test_a_fold_keeps_a_valid_value_valid(capsys: pytest.CaptureFixture[str]) -> None:
    body = HEAD + b"priority: u=1,\r\n  i\r\n\t, x=?0\r\n\r\n"
    code, out, _ = _run(["--strict"], capsys, body)
    assert code == 0
    assert json.loads(out)["canonical"] == "u=1, i, x=?0"


def test_a_fold_belongs_to_the_field_before_it(capsys: pytest.CaptureFixture[str]) -> None:
    body = HEAD + b"priority: u=1\r\nserver: x\r\n priority: u=7\r\n\r\n"
    code, out, _ = _run(["--strict"], capsys, body)
    assert code == 0 and json.loads(out)["urgency"] == 1


@pytest.mark.parametrize("before", [HEAD, HEAD + b"\r\n", b"\n"], ids=["status", "blank", "start"])
def test_an_indented_line_that_continues_no_field_is_no_priority_line(
    before: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    body = before + b" priority: u=1\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    if before.startswith(HEAD):
        assert code == 0 and json.loads(out)["urgency"] == 3, body
    else:
        assert (code, out) == (1, "") and "offset 8" in err, body


def test_bare_values_are_not_folded(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["--strict"], capsys, b"u=1\n i\n")
    assert code == 0 and json.loads(out)["canonical"] == "u=1, i"


@pytest.mark.parametrize("prefix", [b"", HEAD + b"priority: "], ids=["bare", "head"])
def test_only_one_carriage_return_before_a_line_feed_is_dropped(
    prefix: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    body = prefix + b"u=1\r\r\n"
    code, out, err = _run(["--strict"], capsys, body)
    assert (code, out) == (1, ""), body
    assert "offset 3" in err
    code, out, _ = _run([], capsys, body)
    assert code == 0 and json.loads(out)["urgency"] == 3


@pytest.mark.parametrize("space", [b" ", b"\t", b" \t"], ids=lambda space: space.hex())
@pytest.mark.parametrize("end", [b"\r\n", b"\n"], ids=["crlf", "lf"])
def test_a_request_line_with_trailing_whitespace_starts_a_head(
    space: bytes, end: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    body = b"GET / HTTP/1.1" + space + end + b"Host: x" + end + end
    code, out, _ = _run(["--strict"], capsys, body)
    report = json.loads(out)
    assert code == 0, body
    assert (report["urgency"], report["incremental"], report["canonical"]) == (3, False, "")
