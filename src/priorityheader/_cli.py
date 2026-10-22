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
    # Only LF ends a line, with the CR before it dropped (RFC 9112 section 2.2). Every other
    # octet, a lone CR or the extra breaks str.splitlines() knows included, reaches the parser.
    raw = [line.removesuffix("\r") for line in text.split("\n")]
    present = [line for line in (line.strip(_OWS) for line in raw) if line]
    priority = _priority_values([line.strip(_OWS) for line in _unfold(raw)])
    if priority or (present and _START_LINE.match(present[0])):
        return priority
    return present


def _priority_values(lines: list[str]) -> list[str]:
    named = [match for match in map(_FIELD_LINE.match, lines) if match]
    return [m.group(2).strip(_OWS) for m in named if m.group(1).lower() == "priority"]


def _unfold(lines: list[str]) -> list[str]:
    # In a head a line that starts with SP or HTAB continues the field line before it, and
    # the obs-fold is replaced by one SP (RFC 9112 section 5.2) so the value is read whole.
    # Such a line after anything else is no field line and is dropped (section 2.2). The
    # pieces of a field line are joined once at the end, so many folds take linear time.
    unfolded: list[list[str]] = []
    folding = False
    for line in lines:
        if line[:1] in (" ", "\t"):
            if folding:
                unfolded[-1].append(line.strip(_OWS))
            continue
        unfolded.append([line])
        folding = _FIELD_LINE.match(line) is not None
    return [_join(pieces) for pieces in unfolded]


def _join(pieces: list[str]) -> str:
    # The OWS before each line break is part of the obs-fold, and a blank continuation
    # adds nothing, so every fold becomes exactly one SP.
    if len(pieces) == 1:
        return pieces[0]
    return " ".join([pieces[0].rstrip(_OWS), *filter(None, pieces[1:])])


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
