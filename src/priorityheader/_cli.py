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
_START_LINE = re.compile(r"^(HTTP/\S+ \d{3}\b|[A-Z]+ \S+ HTTP/\S+$)")
_OWS = " \t"


def _field_lines(text: str) -> list[str]:
    """Read field values from standard input: a bare value per line, or a message head.

    A head (for example the output of ``curl -sI``) starts with a status or request line or
    carries a Priority line; then only the Priority lines count. Anything else is a list of
    bare values, so a broken value such as ``u:1`` is parsed (and refused by --strict)
    instead of being mistaken for a header.
    """
    lines = [line.strip(_OWS) for line in text.splitlines()]
    present = [line for line in lines if line]
    named = [match for match in map(_FIELD_LINE.match, present) if match]
    priority = [m.group(2).strip(_OWS) for m in named if m.group(1).lower() == "priority"]
    if priority or (present and _START_LINE.match(present[0])):
        return priority
    return present


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
