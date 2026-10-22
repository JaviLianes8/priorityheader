"""Contracts for bytes and bytearray subclasses whose conversion methods misbehave.

The library copies the stored octets with the base type's own slice, so neither
``__bytes__`` nor a Python ``__buffer__`` (Python 3.12 and later) of a caller's subclass
runs or changes what is read.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from priorityheader import (
    Priority,
    PriorityParams,
    build_priority,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    encode_h3_update,
    parse_params,
    parse_priority,
)


class _Escape(BaseException):
    """Stands for an exception a caller's subclass raises that no `except Exception` catches."""


class _RaisingBytes(bytes):
    def __bytes__(self) -> bytes:
        raise _Escape("bytes")

    def __buffer__(self, flags: int) -> memoryview:
        raise _Escape("buffer")


class _RaisingBytearray(bytearray):
    def __bytes__(self) -> bytes:
        raise _Escape("bytes")

    def __buffer__(self, flags: int) -> memoryview:
        raise _Escape("buffer")


class _SwappingBytes(bytes):
    def __bytes__(self) -> bytes:
        return b"garbage"

    def __buffer__(self, flags: int) -> memoryview:
        return memoryview(b"garbage")


_KINDS: list[Callable[[bytes], bytes | bytearray]] = [
    _RaisingBytes,
    _RaisingBytearray,
    _SwappingBytes,
]
_H2 = encode_h2_update(5, "u=0, i")
_H3 = encode_h3_update(4, "u=0, i")


@pytest.mark.parametrize("kind", _KINDS)
def test_the_frame_decoders_read_the_stored_octets_of_a_subclass(
    kind: Callable[[bytes], bytes | bytearray],
) -> None:
    assert decode_h2_update(kind(_H2)) == decode_h2_update(_H2)
    assert decode_h3_update(kind(_H3)) == decode_h3_update(_H3)
    assert decode_h2_update(kind(_H2)).field_value == "u=0, i"


@pytest.mark.parametrize("kind", _KINDS)
def test_the_parsers_read_the_stored_octets_of_a_subclass(
    kind: Callable[[bytes], bytes | bytearray],
) -> None:
    assert parse_priority(kind(b"u=2, i")) == Priority(2, True)
    assert parse_params(kind(b"u=6, x=:YQ==:")) == PriorityParams(6, None, {"x": b"a"})


@pytest.mark.parametrize("kind", [_RaisingBytes, _SwappingBytes])
def test_the_builders_write_the_stored_octets_of_a_subclass(
    kind: Callable[[bytes], bytes],
) -> None:
    assert build_priority(extensions={"x": kind(b"ab")}) == "x=:YWI=:"


@pytest.mark.parametrize("kind", _KINDS)
def test_an_error_quotes_the_stored_octets_of_a_subclass(
    kind: Callable[[bytes], bytes | bytearray],
) -> None:
    with pytest.raises(TypeError) as caught:
        Priority(kind(b"zz"))  # type: ignore[arg-type]
    assert "zz" in str(caught.value)
    assert "garbage" not in str(caught.value)
