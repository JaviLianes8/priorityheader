import io
import json
import sys

import pytest

from priorityheader._cli import main


def _run(
    args: list[str], capsys: pytest.CaptureFixture[str], stdin: bytes = b""
) -> tuple[int, str, str]:
    saved = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin))
    try:
        code = main(args)
    finally:
        sys.stdin = saved
    out, err = capsys.readouterr()
    return code, out, err


def test_a_value_shows_the_resolved_priority(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["u=1, i, x=?0"], capsys)
    assert code == 0
    assert json.loads(out) == {
        "urgency": 1,
        "incremental": True,
        "extensions": {"x": "?0"},
        "canonical": "u=1, i, x=?0",
    }


def test_defaults_are_filled_in_and_dropped_from_the_canonical_form(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _ = _run(["u=3, i=?0"], capsys)
    assert code == 0
    report = json.loads(out)
    assert (report["urgency"], report["incremental"], report["canonical"]) == (3, False, "")


def test_response_mode_shows_absent_members_as_null(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["--response", "u=3"], capsys)
    assert code == 0
    assert json.loads(out) == {
        "urgency": 3,
        "incremental": None,
        "extensions": {},
        "canonical": "u=3",
    }


def test_request_mode_merges_the_response_over_the_request(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _ = _run(["--request", "u=5, i", "u=1"], capsys)
    assert code == 0
    assert json.loads(out) == {"urgency": 1, "incremental": True}


def test_several_arguments_are_field_lines(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["u=1", "i"], capsys)
    assert code == 0 and json.loads(out)["incremental"] is True


def test_standard_input_takes_bare_values(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([], capsys, b"u=2\n\ni\n")
    assert code == 0
    assert (json.loads(out)["urgency"], json.loads(out)["incremental"]) == (2, True)


def test_standard_input_takes_a_message_head(capsys: pytest.CaptureFixture[str]) -> None:
    head = b"HTTP/2 200\r\ncontent-type: text/html\r\nPriority: u=1\r\npriority:\ti\r\n\r\n"
    code, out, _ = _run(["--response"], capsys, head)
    assert code == 0
    report = json.loads(out)
    assert (report["urgency"], report["incremental"]) == (1, True)


def test_a_head_without_a_priority_field_gives_the_defaults(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _ = _run(["--response"], capsys, b"HTTP/1.1 200 OK\r\nServer: x\r\n\r\n")
    assert code == 0
    assert json.loads(out)["urgency"] is None


def test_any_input_octet_is_read(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([], capsys, b"u=1, x=\xff\n")
    assert code == 0 and json.loads(out)["urgency"] == 3


def test_strict_mode_exits_1_with_the_offset(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = _run(["--strict", "u=1,"], capsys)
    assert code == 1 and out == ""
    assert "offset 4" in err


def test_strict_mode_checks_the_request_value_too(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(["--strict", "--request", "u=1,", "u=2"], capsys)
    assert code == 1 and "offset 4" in err


def test_lenient_mode_ignores_a_bad_value(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run(["u=1,"], capsys)
    assert code == 0 and json.loads(out)["urgency"] == 3


def test_response_and_request_cannot_be_combined(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        _run(["--response", "--request", "u=1", "u=2"], capsys)
    assert caught.value.code == 2


def test_a_head_value_after_a_tab_is_read(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run([], capsys, b"HTTP/2 200\r\npriority:\tu=1\r\n\r\n")
    assert code == 0 and json.loads(out)["urgency"] == 1


# Only LF ends a field line (RFC 9112 section 2.2 lets a reader drop the CR before it); the
# other line breaks str.splitlines() knows reach the parser and fail there.
BREAKS = [b"\x0b", b"\x0c", b"\x1c", b"\x1d", b"\x1e", b"\x85", b"\r"]


@pytest.mark.parametrize("octet", BREAKS, ids=lambda octet: octet.hex())
def test_only_a_line_feed_ends_a_standard_input_line(
    octet: bytes, capsys: pytest.CaptureFixture[str]
) -> None:
    for body in (b"u=1" + octet + b"i\n", b"HTTP/1.1 200 OK\r\npriority: u=1" + octet + b"i\r\n"):
        code, out, err = _run(["--strict"], capsys, body)
        assert (code, out) == (1, ""), body
        assert "offset 3" in err
        code, out, _ = _run(["--response"], capsys, body)
        assert code == 0 and json.loads(out)["urgency"] is None


def test_optional_whitespace_around_a_standard_input_line_is_dropped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _ = _run(["--strict"], capsys, b"\tu=1 \t\r\n \ti\t\n")
    assert code == 0
    assert json.loads(out)["canonical"] == "u=1, i"
