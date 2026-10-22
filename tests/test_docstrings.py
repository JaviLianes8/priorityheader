"""Every docstring example of the public API runs, wherever the collector would miss it.

pytest's doctest collector finds an example through the module that defines it; this test
walks ``__all__`` itself and pins how many examples it ran, so an example that stops being
collected, or is lost, fails.
"""

from __future__ import annotations

import doctest
import inspect

import priorityheader

#: Examples per public object and its own methods and properties; a new or lost one fails.
EXPECTED = {
    "priorityheader": 6,
    "Date": 3,
    "DisplayString": 3,
    "FrameError": 2,
    "Priority": 5,
    "PriorityError": 2,
    "PriorityParams": 5,
    "PriorityUpdate": 4,
    "PriorityUpdate.priority": 3,
    "Token": 2,
    "build_params": 3,
    "build_priority": 4,
    "decode_h2_update": 2,
    "decode_h3_update": 2,
    "encode_h2_update": 2,
    "encode_h3_update": 2,
    "merge_priority": 3,
    "parse_params": 3,
    "parse_priority": 4,
}


def _docstrings() -> dict[str, str]:
    found = {"priorityheader": priorityheader.__doc__ or ""}
    for name in priorityheader.__all__:
        obj = getattr(priorityheader, name)
        if not (inspect.isclass(obj) or inspect.isfunction(obj)):
            continue
        found[name] = inspect.getdoc(obj) or ""
        if inspect.isclass(obj):
            for attr, member in vars(obj).items():
                doc = getattr(member, "__doc__", None)
                if not attr.startswith("_") and doc and ">>>" in doc:
                    found[f"{name}.{attr}"] = doc
    return found


def test_every_public_docstring_example_runs_and_none_is_skipped() -> None:
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    counts: dict[str, int] = {}
    for name, doc in sorted(_docstrings().items()):
        test = parser.get_doctest(doc, {}, name, f"{name} docstring", 0)
        result = runner.run(test, clear_globs=True)
        assert result.failed == 0, name
        counts[name] = result.attempted
    assert counts == EXPECTED
