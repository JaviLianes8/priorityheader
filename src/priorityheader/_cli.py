"""Command line: show what a Priority field asks for, as JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence

from ._build import build_params, build_priority
from ._errors import PriorityError
from ._model import PriorityParams
from ._parse import merge_priority, parse_params
from ._sfwrite import serialize_member

EXIT_INVALID = 1
_FIELD_LINE = re.compile(r"^([!#$%&'*+.^_`|~0-9A-Za-z-]+):(.*)$")


def _field_lines(text: str) -> list[str]:
    """Read field values from standard input: a bare value per line, or a message head.

    In a head (for example the output of ``curl -sI``) only the Priority lines count.
    """
    lines = [line.strip(" \t") for line in text.splitlines()]
    named = [match for match in map(_FIELD_LINE.match, lines) if match]
    if not named:
        return [line for line in lines if line]
    return [m.group(2).strip(" \t") for m in named if m.group(1).lower() == "priority"]


def _report(params: PriorityParams, *, response: bool) -> dict[str, object]:
    extensions = {key: serialize_member(value) for key, value in params.extensions.items()}
    if response:
        return {
            "urgency": params.urgency,
            "incremental": params.incremental,
            "extensions": extensions,
            "canonical": build_params(params),
        }
    priority = params.resolve()
    return {
        "urgency": priority.urgency,
        "incremental": priority.incremental,
        "extensions": extensions,
        "canonical": build_priority(*priority, extensions=params.extensions),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="priorityheader",
        description="Show the priority a Priority field value asks for (RFC 9218). Values "
        "given as arguments are field lines; without arguments the lines are read from "
        "standard input, either bare values or a message head such as curl -sI prints. "
        "Exit status 1 means a value that does not parse in --strict mode, 2 a usage error.",
    )
    parser.add_argument("value", nargs="*", help="Priority field values (one per field line)")
    parser.add_argument("--strict", action="store_true", help="fail on a value that does not parse")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--response", action="store_true", help="show the explicit members, null when absent"
    )
    mode.add_argument(
        "--request",
        metavar="VALUE",
        help="treat the value as a response and merge it over this request value",
    )
    args = parser.parse_args(argv)
    if args.value:
        lines = list(args.value)
    else:
        # ISO-8859-1 maps every octet, so no input byte can stop the program.
        lines = _field_lines(sys.stdin.buffer.read().decode("iso-8859-1"))
    try:
        params = parse_params(lines, strict=args.strict)
        if args.request is not None:
            parse_params(args.request, strict=args.strict)
            merged = merge_priority(args.request, lines)
            report: dict[str, object] = {
                "urgency": merged.urgency,
                "incremental": merged.incremental,
            }
        else:
            report = _report(params, response=args.response)
    except PriorityError as error:
        print(f"priorityheader: {error}", file=sys.stderr)
        return EXIT_INVALID
    print(json.dumps(report, indent=2))
    return 0
