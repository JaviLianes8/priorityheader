from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def read_upstream(name: str) -> str:
    """Return a third-party reference file as text.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))[name]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body.decode("utf-8")


@pytest.fixture(scope="session")
def rfc9218() -> str:
    """RFC 9218, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9218.txt")


@pytest.fixture(scope="session")
def rfc9113() -> str:
    """RFC 9113, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9113.txt")


@pytest.fixture(scope="session")
def rfc9114() -> str:
    """RFC 9114, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9114.txt")


@pytest.fixture(scope="session")
def rfc9000() -> str:
    """RFC 9000, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9000.txt")


@pytest.fixture(scope="session")
def rfc9651() -> str:
    """RFC 9651, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("rfc9651.txt")


@pytest.fixture(scope="session")
def iana_xml() -> str:
    """The IANA HTTP Priority registry, see tests/upstream/MANIFEST.json for its source."""
    return read_upstream("http-priority.xml")
