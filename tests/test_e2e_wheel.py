"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with PRIORITYHEADER_E2E=1.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("PRIORITYHEADER_E2E") != "1",
    reason="set PRIORITYHEADER_E2E=1 to build and install",
)

PROGRAM = r"""
import importlib.metadata, importlib.resources
import priorityheader
from priorityheader import (
    FrameError, Priority, PriorityError, PriorityParams, Token, build_params, build_priority,
    decode_h2_update, decode_h3_update, encode_h2_update, encode_h3_update, merge_priority,
    parse_params, parse_priority,
)

assert "site-packages" in priorityheader.__file__, priorityheader.__file__
assert importlib.metadata.version("priorityheader") == priorityheader.__version__
assert importlib.resources.files("priorityheader").joinpath("py.typed").is_file()

assert parse_priority(["u=1", b"i"]) == Priority(1, True)
assert parse_priority("u=4, i, @broken") == Priority()
assert merge_priority("u=5, i", "u=1") == Priority(1, True)
params = parse_params("u=3, i=?0, x=(1 a)")
assert params == PriorityParams(3, False, {"x": (1, Token("a"))})
assert build_params(params) == "u=3, i=?0, x=(1 a)"
assert build_priority(0, True) == "u=0, i"
assert decode_h2_update(encode_h2_update(5, "u=0")).priority() == Priority(0, False)
assert decode_h3_update(encode_h3_update(3, "i", target="push")).target == "push"
try:
    parse_priority("u=1,", strict=True)
except PriorityError as error:
    assert error.offset == 4
else:
    raise AssertionError("expected PriorityError")
try:
    decode_h2_update(bytes.fromhex("000004100000000001") + bytes(4))
except FrameError as error:
    assert error.code == "PROTOCOL_ERROR"
else:
    raise AssertionError("expected FrameError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("priorityheader-*.whl")
    (sdist,) = dist.glob("priorityheader-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "priorityheader/py.typed" in names and "priorityheader/__main__.py" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    text = zipfile.ZipFile(wheel).read(entry_points).decode()
    assert "priorityheader = priorityheader._cli:main" in text
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]
    assert "tests/upstream/MANIFEST.json" in listing and "scripts/fetch_upstream.py" in listing
    assert "tests/test_sources.py" in listing and "README.md" in listing
    assert not [name for name in listing if name.startswith(("tests/upstream/sf", "scratchpad"))]
    assert not [name for name in listing if name.endswith((".txt", ".xml")) and "upstream" in name]
    assert not [name for name in listing if "IMPROVEMENTS" in name]

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    head = b"HTTP/2 200\r\ncontent-type: image/png\r\npriority: u=1\r\n\r\n"
    script = bindir / ("priorityheader.exe" if sys.platform == "win32" else "priorityheader")
    for command in ([script], [python, "-m", "priorityheader"]):
        shown = _run(*command, "--response", cwd=work, stdin=head)
        assert shown.returncode == 0, shown.stderr
        report = json.loads(shown.stdout)
        assert report["urgency"] == 1 and report["incremental"] is None
        merged = _run(*command, "--request", "u=5, i", "u=1", cwd=work)
        assert json.loads(merged.stdout) == {"urgency": 1, "incremental": True}
    failed = _run(script, "--strict", "u=1,", cwd=work)
    assert failed.returncode == 1 and b"trailing comma" in failed.stderr
