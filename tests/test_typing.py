"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from priorityheader import PriorityParams, build_params, build_priority, decode_h2_update
from priorityheader import decode_h3_update, merge_priority, parse_params, parse_priority
reveal_type(parse_priority("u=1"))
reveal_type(parse_priority("u=1").urgency)
reveal_type(parse_params("u=1").urgency)
reveal_type(parse_params("u=1").incremental)
reveal_type(merge_priority(None, "u=1"))
reveal_type(build_priority(1))
reveal_type(build_params(PriorityParams()))
reveal_type(decode_h2_update(b"").element_id)
reveal_type(decode_h3_update(b"").target)
parse_priority("u=1", True)
parse_priority(3)
build_priority("1")
build_priority(1, 1)
PriorityParams(urgency="1")
parse_priority(["u=1", b"i"], strict=True)
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    paths = f"mypy_path = {SRC.as_posix()}\n" if SRC.is_dir() else ""
    config.write_text(f"[mypy]\n{paths}", encoding="utf-8")
    cache = str(folder / "cache")
    # The interpreter running the tests decides where the package is found: the source
    # tree when it exists, otherwise the installed wheel (as in the sdist's own suite).
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache]
    args += ["--python-executable", sys.executable, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def _revealed(output: str) -> list[str]:
    # Older mypy releases spell builtins with their module, newer ones without it.
    return [t.replace("builtins.", "") for t in re.findall(r'Revealed type is "(.+)"', output)]


def test_functions_return_the_documented_types(mypy_output: str) -> None:
    assert _revealed(mypy_output) == [
        "tuple[int, bool, fallback=priorityheader._model.Priority]",
        "int",
        "int | None",
        "bool | None",
        "tuple[int, bool, fallback=priorityheader._model.Priority]",
        "str",
        "str",
        "int",
        "Literal['stream'] | Literal['push']",
    ]


def test_wrong_arguments_are_type_errors(mypy_output: str) -> None:
    lines = sorted({int(n) for n in re.findall(r"snippet\.py:(\d+): error:", mypy_output)})
    # Lines 13 to 17 of the snippet are the wrong calls; line 18 is a valid one.
    assert lines == [13, 14, 15, 16, 17], mypy_output
