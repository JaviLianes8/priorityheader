"""Seeded property and fuzz tests: no crash, no untyped error, round trips, linear time."""

from __future__ import annotations

import contextlib
import gc
import io
import json
import random
import time
from collections.abc import Callable

import pytest
import sfgen

from priorityheader import (
    FrameError,
    Priority,
    PriorityError,
    PriorityParams,
    build_params,
    build_priority,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    encode_h3_update,
    merge_priority,
    parse_params,
    parse_priority,
)
from priorityheader._cli import main

SEEDS = [11, 12, 13]


@pytest.mark.parametrize("seed", SEEDS)
def test_parsing_never_crashes_and_strict_agrees_with_lenient(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(20_000):
        text = sfgen.field(rng)
        lenient = parse_params(text)
        try:
            strict = parse_params(text, strict=True)
        except PriorityError as error:
            assert type(error) is PriorityError
            assert error.offset is not None and 0 <= error.offset <= len(text), text
            assert len(str(error)) < 120
            assert lenient == PriorityParams()
            assert parse_priority(text) == Priority()
        else:
            assert strict == lenient
            assert parse_priority(text, strict=True) == lenient.resolve()
        assert parse_params(text.encode("latin-1")) == lenient


@pytest.mark.parametrize("seed", SEEDS)
def test_what_parses_builds_back_to_the_same_members(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(10_000):
        params = parse_params(sfgen.dictionary(rng))
        built = build_params(params)
        assert parse_params(built, strict=True) == params, built
        assert build_params(parse_params(built)) == built
        resolved = params.resolve()
        request = build_priority(*resolved, extensions=params.extensions)
        assert parse_priority(request, strict=True) == resolved
        assert parse_params(request).extensions == params.extensions


@pytest.mark.parametrize("seed", SEEDS)
def test_merge_takes_each_member_from_the_response_when_present(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(10_000):
        request, response = sfgen.field(rng), sfgen.field(rng)
        merged = merge_priority(request, response)
        base, over = parse_priority(request), parse_params(response)
        urgency = base.urgency if over.urgency is None else over.urgency
        incremental = base.incremental if over.incremental is None else over.incremental
        assert merged == Priority(urgency, incremental)


@pytest.mark.parametrize("seed", SEEDS)
def test_frames_round_trip_and_decoders_only_raise_frame_errors(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(5_000):
        value = build_params(parse_params(sfgen.dictionary(rng)))
        stream = rng.randint(1, 2**31 - 1)
        assert decode_h2_update(encode_h2_update(stream, value)).element_id == stream
        element = rng.randint(0, 2**62 - 1)
        push = decode_h3_update(encode_h3_update(element, value, target="push"))
        assert (push.element_id, push.field_value) == (element, value)
        noise = rng.randbytes(rng.randint(0, 24))
        for blob in (noise, bytes([0, 0, len(noise), 0x10, 0, 0, 0, 0, 0]) + noise):
            for decode in (decode_h2_update, decode_h3_update):
                with contextlib.suppress(FrameError):
                    decoded = decode(blob)
                    with contextlib.suppress(FrameError):
                        decoded.priority(strict=True)


@pytest.mark.parametrize("seed", SEEDS)
def test_the_command_line_never_crashes(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(500):
        args = [sfgen.field(rng) for _ in range(rng.randint(1, 2))]
        mode = rng.choice([[], ["--strict"], ["--response"], [f"--request={sfgen.field(rng)}"]])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([*mode, "--", *args])
        assert code in (0, 1)
        if code == 0:
            assert isinstance(json.loads(out.getvalue()), dict)
        else:
            assert err.getvalue().startswith("priorityheader: ") and len(err.getvalue()) < 200


SHAPES: dict[str, Callable[[int], str]] = {
    "members": lambda n: "a, " * n + "a",
    "repeated key": lambda n: "a=1, " * n + "a",
    "parameters": lambda n: "a" + ";b=1" * n,
    "inner list": lambda n: "a=(" + "1 " * n + ")",
    "unterminated list": lambda n: "a=(" + "1 " * n,
    "escapes": lambda n: 'a="' + '\\"' * n + '"',
    "unterminated string": lambda n: 'a="' + "x" * n,
    "display": lambda n: 'a=%"' + "%41" * n + '"',
    "bytes": lambda n: "a=:" + "QUFB" * n + ":",
    "unterminated bytes": lambda n: "a=:" + "Q" * n,
    "token": lambda n: "a=b" + "/" * n,
    "key": lambda n: "a" * n,
    "spaces": lambda n: " " * n + "a" + " " * n,
    "trailing garbage": lambda n: "u=1, " + "?" * n,
}


def _best_seconds(*texts: str) -> list[float]:
    # CPU time of this process per call, not the wall clock, so load from other processes
    # does not count. The process clock ticks coarsely (15.6 ms on Windows), so each sample
    # repeats the call for at least 0.2 s. The inputs are measured in turn, with the
    # collector paused, and the best of three samples is kept for each.
    best = [float("inf")] * len(texts)
    enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(3):
            for index, text in enumerate(texts):
                calls, start, spent = 0, time.process_time(), 0.0
                while spent < 0.2:
                    parse_params(text)
                    calls += 1
                    spent = time.process_time() - start
                best[index] = min(best[index], spent / calls)
    finally:
        if enabled:
            gc.enable()
    return best


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_parsing_time_grows_linearly(shape: str) -> None:
    small, large = _best_seconds(SHAPES[shape](20_000), SHAPES[shape](80_000))
    # Four times the input takes about four times as long; quadratic growth would be 16.
    assert large < 10 * small, shape
