"""Read the HTTP Priority header into urgency and incremental flags."""

from __future__ import annotations

from ._dict import parse_dictionary
from ._model import DEFAULT_URGENCY, MAX_URGENCY, MIN_URGENCY, Priority


def parse_priority(header: str) -> Priority:
    """Return the urgency and incremental flag carried by a Priority header.

    The header is an RFC 9218 structured-field dictionary: ``u`` an integer
    urgency and ``i`` a boolean incremental flag. A missing member, a member of
    the wrong type, or an urgency outside 0..7 falls back to its default (urgency
    3, not incremental), so a malformed header is never an error.
    """
    members = parse_dictionary(header)
    return Priority(_read_urgency(members.get("u")), _read_incremental(members.get("i")))


def _read_urgency(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        return DEFAULT_URGENCY
    if MIN_URGENCY <= value <= MAX_URGENCY:
        return value
    return DEFAULT_URGENCY


def _read_incremental(value: object) -> bool:
    return value if isinstance(value, bool) else False
