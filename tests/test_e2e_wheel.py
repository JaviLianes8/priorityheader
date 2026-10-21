"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with PRIORITYHEADER_E2E=1. With
PRIORITYHEADER_E2E_PYPI=1 as well, the release on PyPI is installed first and upgraded in
place to the built wheel.
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
import copy, pickle
assert pickle.loads(pickle.dumps(params)) == copy.deepcopy(params) == params
assert repr(Priority(1, True)) == "Priority(urgency=1, incremental=True)"
for bad in (lambda: Priority(9), lambda: encode_h3_update(4, "u=1", target="x")):
    try:
        bad()
    except PriorityError:
        pass
    else:
        raise AssertionError("expected PriorityError")
print("e2e ok", priorityheader.__version__)
"""

# What 0.2.0 on PyPI does with the calls whose behaviour 1.0.0 keeps.
OLD_PROGRAM = r"""
from priorityheader import Priority, build_params, merge_priority, parse_params, parse_priority
assert parse_priority(["u=1", b"i"]) == Priority(1, True)
assert merge_priority("u=5, i", "u=1") == Priority(1, True)
assert build_params(parse_params("u=3, i=?0, x=(1 a)")) == "u=3, i=?0, x=(1 a)"
import priorityheader
print("old ok", priorityheader.__version__)
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    dist = tmp_path_factory.mktemp("dist")
    result = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert result.returncode == 0, result.stderr
    (wheel,) = dist.glob("priorityheader-*.whl")
    (sdist,) = dist.glob("priorityheader-*.tar.gz")
    return wheel, sdist


def _venv(where: Path) -> tuple[Path, Path]:
    venv.create(where, with_pip=True)
    bindir = where / ("Scripts" if sys.platform == "win32" else "bin")
    return bindir, bindir / "python"


def _check_cli(bindir: Path, python: Path, work: Path) -> None:
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


def test_installed_wheel_end_to_end(tmp_path: Path, built: tuple[Path, Path]) -> None:
    wheel, sdist = built
    names = zipfile.ZipFile(wheel).namelist()
    assert "priorityheader/py.typed" in names and "priorityheader/__main__.py" in names
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    assert any(name.endswith("licenses/LICENSE") for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    text = zipfile.ZipFile(wheel).read(entry_points).decode()
    assert "priorityheader = priorityheader._cli:main" in text
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]
    assert "tests/upstream/MANIFEST.json" in listing and "scripts/fetch_upstream.py" in listing
    assert "tests/test_sources.py" in listing and "README.md" in listing
    assert "GUIDE.md" in listing and "LICENSE" in listing
    assert not [name for name in listing if name.startswith(("tests/upstream/sf", "scratchpad"))]
    assert not [name for name in listing if name.endswith((".txt", ".xml")) and "upstream" in name]
    assert not [name for name in listing if "IMPROVEMENTS" in name or "CERT-1.0" in name]

    bindir, python = _venv(tmp_path / "venv")
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr
    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().split() == ["e2e", "ok", "1.0.0"]
    _check_cli(bindir, python, work)


@pytest.mark.skipif(
    os.environ.get("PRIORITYHEADER_E2E_PYPI") != "1",
    reason="set PRIORITYHEADER_E2E_PYPI=1 to install the release from PyPI",
)
def test_upgrade_in_place_from_the_pypi_release(tmp_path: Path, built: tuple[Path, Path]) -> None:
    bindir, python = _venv(tmp_path / "venv")
    work = tmp_path / "work"
    work.mkdir()
    old = _run(python, "-m", "pip", "install", "-q", "--no-cache-dir", "priorityheader==0.2.0")
    assert old.returncode == 0, old.stderr
    before = _run(python, "-I", "-c", OLD_PROGRAM, cwd=work)
    assert before.stdout.decode().split() == ["old", "ok", "0.2.0"], before.stderr
    upgraded = _run(python, "-m", "pip", "install", "-q", "--upgrade", built[0])
    assert upgraded.returncode == 0, upgraded.stderr
    for program, expected in ((OLD_PROGRAM, "old"), (PROGRAM, "e2e")):
        after = _run(python, "-I", "-c", program, cwd=work)
        assert after.stdout.decode().split() == [expected, "ok", "1.0.0"], after.stderr
    _check_cli(bindir, python, work)
