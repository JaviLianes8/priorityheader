"""Run the httpwg structured field test corpus against the parser and the serializer.

The corpus files are fetched into tests/upstream/sf (see MANIFEST.json); these tests skip
until `python scripts/fetch_upstream.py` has fetched them. Top-level Lists are out of scope
for parsing (the Priority field is a Dictionary) but their items still exercise the writer.
"""

from __future__ import annotations

import base64
import json
from decimal import Decimal
from typing import Any

import pytest
from conftest import read_upstream

from priorityheader import Date, DisplayString, PriorityError, Token
from priorityheader._sf import Reader
from priorityheader._sfdict import parse_dictionary, parse_item
from priorityheader._sfwrite import serialize_bare_item, serialize_key, serialize_params

PARSE_FILES = [
    "binary",
    "boolean",
    "date",
    "dictionary",
    "display-string",
    "examples",
    "item",
    "key-generated",
    "large-generated",
    "number",
    "number-generated",
    "param-dict",
    "string",
    "string-generated",
    "token",
    "token-generated",
]
SERIALISATION_FILES = ["key-generated", "number", "string-generated", "token-generated"]


def _plain(value: Any) -> Any:
    """Convert a parsed value to the corpus JSON shape."""
    if isinstance(value, bool):
        return value
    if isinstance(value, Date):
        return {"__type": "date", "value": int(value)}
    if isinstance(value, Token):
        return {"__type": "token", "value": str(value)}
    if isinstance(value, DisplayString):
        return {"__type": "displaystring", "value": str(value)}
    if isinstance(value, bytes):
        return {"__type": "binary", "value": base64.b32encode(value).decode()}
    if isinstance(value, list):
        return [[_plain(item), _params(params)] for item, params in value]
    return value


def _params(params: dict[str, Any]) -> list[list[Any]]:
    return [[key, _plain(value)] for key, value in params.items()]


def _value(data: Any) -> Any:
    """Convert a corpus bare item to the library's Python type."""
    if isinstance(data, dict):
        kind, raw = data["__type"], data["value"]
        if kind == "binary":
            return base64.b32decode(raw)
        return {"token": Token, "date": Date, "displaystring": DisplayString}[kind](raw)
    return data


def _write_item(item: list[Any]) -> str:
    value, params = item
    params_text = serialize_params({key: _value(v) for key, v in params})
    if isinstance(value, list):
        inner = " ".join(_write_item(member) for member in value)
        return f"({inner}){params_text}"
    return serialize_bare_item(_value(value)) + params_text


def _write(case: dict[str, Any]) -> str:
    expected = case["expected"]
    if case["header_type"] == "item":
        return _write_item(expected)
    if case["header_type"] == "list":
        return ", ".join(_write_item(member) for member in expected)
    parts = []
    for key, (value, params) in expected:
        name = serialize_key(key)
        if value is True:
            parts.append(name + serialize_params({k: _value(v) for k, v in params}))
        else:
            parts.append(f"{name}={_write_item([value, params])}")
    return ", ".join(parts)


def _parse(case: dict[str, Any]) -> Any:
    text = ", ".join(case["raw"])
    if case["header_type"] == "dictionary":
        parsed = parse_dictionary(text)
        return [[key, [_plain(v), _params(p)]] for key, (v, p) in parsed.items()]
    r = Reader(text)
    if not text.isascii():
        raise PriorityError("structured fields are ASCII")
    r.skip(" ")
    item, params = parse_item(r)
    r.skip(" ")
    if not r.done():
        raise PriorityError("trailing text")
    return [_plain(item), _params(params)]


@pytest.mark.parametrize("name", PARSE_FILES)
def test_the_corpus_file_parses_as_expected(name: str) -> None:
    cases = json.loads(read_upstream(f"sf/{name}.json"), parse_float=Decimal)
    checked = 0
    for case in cases:
        if case["header_type"] == "list":
            continue
        try:
            got = _parse(case)
        except PriorityError:
            assert case.get("must_fail") or case.get("can_fail"), case["name"]
        else:
            assert not case.get("must_fail"), case["name"]
            assert got == case["expected"], case["name"]
        checked += 1
    assert checked > 0


@pytest.mark.parametrize("name", PARSE_FILES)
def test_the_corpus_file_serializes_to_its_canonical_form(name: str) -> None:
    cases = json.loads(read_upstream(f"sf/{name}.json"), parse_float=Decimal)
    checked = 0
    for case in cases:
        if case.get("must_fail") or (not case.get("expected") and case["header_type"] != "item"):
            continue
        canonical = case.get("canonical", case.get("raw"))
        assert _write(case) == ", ".join(canonical), case["name"]
        checked += 1
    assert checked > 0


@pytest.mark.parametrize("name", SERIALISATION_FILES)
def test_the_serialisation_tests_pass(name: str) -> None:
    cases = json.loads(read_upstream(f"sf/serialisation/{name}.json"), parse_float=Decimal)
    for case in cases:
        if case.get("must_fail"):
            with pytest.raises(PriorityError):
                _write(case)
        else:
            assert _write(case) == ", ".join(case["canonical"]), case["name"]
    assert cases
