"""The structured field reader and writer against http-sf, an independent implementation.

http-sf is not a dependency; the tests skip when it is not installed (``pip install
http-sf``). The version used for the 1.0.0 certification is in CERT-1.0-REPORT.md.
"""

from __future__ import annotations

import datetime
import random
import re
from decimal import Decimal
from typing import Any

import pytest
import sfgen

from priorityheader import (
    Date,
    DisplayString,
    PriorityError,
    PriorityParams,
    Token,
    build_params,
)
from priorityheader._sfdict import parse_dictionary
from priorityheader._sfwrite import serialize_key, serialize_member, serialize_params

# Where http-sf departs from RFC 9651. It is laxer about leading zeros: an Integer of more
# than 15 digits passes when its value fits. It is stricter in two places: it turns Dates
# into datetime objects (so a Date outside years 1..9999, or before 1970 on Windows, fails),
# and it refuses a Byte Sequence without "=" padding, which section 4.2.7 says SHOULD be read.
_LONG_INTEGER = re.compile(r"(?<![\w.%:\"])(-?)(0\d{15,})(?![\d.])")
_ORACLE_LIMITS = ("Date value out of range", "Binary Sequence failed to decode")


def _ours(value: Any) -> Any:
    if isinstance(value, list):
        return ("list", [(_ours(item), _params(p)) for item, p in value])
    for kind in (bool, Date, Token, DisplayString, bytes, str, Decimal, int):
        if isinstance(value, kind):
            return (kind.__name__, value if kind is not Date else int(value))
    raise AssertionError(type(value))


def _params(params: dict[str, Any]) -> list[tuple[str, Any]]:
    return [(key, _ours(value)) for key, value in params.items()]


def _theirs(value: Any, sf: Any) -> Any:
    if isinstance(value, list):
        return ("list", [(_theirs(item, sf), _tparams(p, sf)) for item, p in value])
    if isinstance(value, datetime.datetime):
        return ("Date", int(value.timestamp()))
    pairs = [(bool, "bool"), (sf.Token, "Token"), (sf.DisplayString, "DisplayString")]
    pairs += [(bytes, "bytes"), (str, "str"), (float, "Decimal"), (Decimal, "Decimal")]
    pairs += [(int, "int")]
    for kind, name in pairs:
        if isinstance(value, kind):
            if name == "Decimal":
                return (name, Decimal(str(value)))
            return (name, str(value) if name in ("Token", "DisplayString") else value)
    raise AssertionError(type(value))


def _tparams(params: dict[str, Any], sf: Any) -> list[tuple[str, Any]]:
    return [(key, _theirs(value, sf)) for key, value in params.items()]


def _reads_alike(sf: Any, members: dict[str, Any], ours: Any) -> bool:
    try:
        again = sf.parse(_canonical(members).encode("ascii"), tltype="dictionary")
    except sf.StructuredFieldError:
        return False
    return bool([(k, _theirs(v, sf), _tparams(p, sf)) for k, (v, p) in again.items()] == ours)


def _has_far_date(members: dict[str, Any]) -> bool:
    found: list[Any] = []
    for value, params in members.values():
        found += [item for item, _ in value] if isinstance(value, list) else [value]
        found += list(params.values())
        for _, inner in value if isinstance(value, list) else []:
            found += list(inner.values())
    return any(not _fits_datetime(item) for item in found if isinstance(item, Date))


def _fits_datetime(seconds: int) -> bool:
    # The oracle's own limit, which depends on the platform (Windows stops at year 3000).
    try:
        datetime.datetime.fromtimestamp(seconds, tz=datetime.timezone.utc)
    except (OverflowError, OSError, ValueError):
        return False
    return True


def _canonical(members: dict[str, Any]) -> str:
    out = []
    for key, (value, params) in members.items():
        if isinstance(value, list):
            items = " ".join(serialize_member(i) + serialize_params(p) for i, p in value)
            text = f"{serialize_key(key)}=({items})"
        else:
            text = key if value is True else f"{key}={serialize_member(value)}"
        out.append(text + serialize_params(params))
    return ", ".join(out)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_dictionaries_read_like_http_sf(seed: int) -> None:
    sf = pytest.importorskip("http_sf")
    rng = random.Random(seed)
    agreed = limits = 0
    for _ in range(20_000):
        text = sfgen.field(rng)
        try:
            members = parse_dictionary(text)
            ours: Any = [(k, _ours(v), _params(p)) for k, (v, p) in members.items()]
        except PriorityError:
            ours = "fails"
        try:
            parsed = sf.parse(text.encode("latin-1"), tltype="dictionary")
            theirs: Any = [(k, _theirs(v, sf), _tparams(p, sf)) for k, (v, p) in parsed.items()]
        except sf.StructuredFieldError as error:
            if ours != "fails" and str(error) in _ORACLE_LIMITS:
                # Our canonical form pads every Byte Sequence; then only a Date the oracle
                # cannot hold as a datetime may still stop it.
                assert _reads_alike(sf, members, ours) or _has_far_date(members), text
                limits += 1
                continue
            theirs = "fails"
        except (OverflowError, OSError, ValueError):
            limits += 1
            continue
        if ours == "fails" and theirs != "fails" and _LONG_INTEGER.search(text):
            # RFC 9651 section 4.2.4 step 5 counts leading zeros among the 15 digits an
            # Integer may have; the oracle checks the value instead. Without the zeros
            # the two must agree.
            shorter = _LONG_INTEGER.sub(lambda m: m.group(1) + m.group(2).lstrip("0"), text)
            members = parse_dictionary(shorter)
            ours = [(k, _ours(v), _params(p)) for k, (v, p) in members.items()]
            limits += 1
        assert ours == theirs, text
        agreed += 1
    assert agreed > 15_000 and limits < 4_000


@pytest.mark.parametrize("seed", [4, 5])
def test_built_values_read_back_through_http_sf(seed: int) -> None:
    sf = pytest.importorskip("http_sf")
    rng = random.Random(seed)
    for _ in range(5_000):
        text = sfgen.dictionary(rng)
        try:
            members = parse_dictionary(text)
        except PriorityError:
            continue
        extensions = _extensions(members)
        built = build_params(PriorityParams(extensions=extensions))
        parsed = sf.parse(built.encode("ascii"), tltype="dictionary")
        theirs = {key: _theirs(value, sf) for key, (value, _) in parsed.items()}
        expected = {k: _no_params(_ours(members[k][0])) for k in extensions}
        assert theirs == expected, text
        assert built == "" or sf.ser(parsed) == built, text


def _has_date(value: Any) -> bool:
    items = [item for item, _ in value] if isinstance(value, list) else [value]
    return any(isinstance(item, Date) for item in items)


def _extensions(members: dict[str, Any]) -> dict[str, Any]:
    # Dates are left out: the oracle turns them into datetime objects and may not hold them.
    out: dict[str, Any] = {}
    for key, (value, _) in members.items():
        if key not in ("u", "i") and not _has_date(value):
            out[key] = tuple(item for item, _ in value) if isinstance(value, list) else value
    return out


def _no_params(value: Any) -> Any:
    # build_params keeps the items of an inner list but not their parameters.
    if value[0] == "list":
        return ("list", [(item, []) for item, _ in value[1]])
    return value
