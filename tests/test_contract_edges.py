"""Contracts added by the author mutation round of the 1.0.0 certification.

Each pins a behaviour a deliberate bug changed without any other test failing.
"""

from __future__ import annotations

import pytest

from priorityheader import Priority, PriorityParams, build_params, parse_params

# The httpwg corpus (binary.json at 781ba38, see tests/upstream/MANIFEST.json) marks these
# "can_fail"; RFC 9651 section 4.2.7 says a parser SHOULD NOT fail on missing padding or
# non-zero pad bits, and this library reads all three.
PADDING = {
    "unpadded": ("x=:aGVsbG8:", b"hello"),
    "extra padding": ("x=:aGVsbG8==:", b"hello"),
    "non-zero pad bits": ("x=:iZ==:", b"\x89"),
}


@pytest.mark.parametrize("name", sorted(PADDING))
def test_byte_sequences_the_corpus_lets_a_parser_accept_are_read(name: str) -> None:
    text, value = PADDING[name]
    assert parse_params(text, strict=True).extensions["x"] == value


def test_padding_in_the_middle_still_fails() -> None:
    assert parse_params("x=:a=GVsbG8=:").extensions == {}


class _LooksLikeParams:
    urgency = 1
    incremental = True
    extensions: tuple[object, ...] = ()


@pytest.mark.parametrize("value", [Priority(1, True), _LooksLikeParams(), None])
def test_build_params_takes_only_priority_params(value: object) -> None:
    with pytest.raises(TypeError, match="params must be PriorityParams"):
        build_params(value)  # type: ignore[arg-type]
    assert build_params(PriorityParams(1, True)) == "u=1, i"


class _ForgedReprBytes(bytes):
    def __repr__(self) -> str:
        return "<forged message text> " + "z" * 100


class _ForgedReprBytearray(bytearray):
    def __repr__(self) -> str:
        return "<forged message text> " + "z" * 100


@pytest.mark.parametrize("kind", [_ForgedReprBytes, _ForgedReprBytearray])
def test_a_long_bytes_value_is_quoted_from_its_octets_never_its_repr(kind: type) -> None:
    with pytest.raises(TypeError) as caught:
        Priority(kind(b"x" * 100))
    prefix = "bytearray(b'" if kind is _ForgedReprBytearray else "b'"
    expected = (prefix + "x" * 100)[:60] + "..."
    assert str(caught.value) == f"urgency must be an int, got {expected}"
