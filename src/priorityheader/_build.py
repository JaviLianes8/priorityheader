"""Render urgency and incremental flags into a Priority header value."""

from __future__ import annotations

from ._errors import PriorityError
from ._model import DEFAULT_URGENCY, MAX_URGENCY, MIN_URGENCY


def build_priority(urgency: int = DEFAULT_URGENCY, incremental: bool = False) -> str:
    """Render a Priority header value, dropping anything left at its default.

    ``urgency`` must be an integer in 0..7 and ``incremental`` a boolean. The
    default urgency (3) and a false incremental flag are omitted, since a peer
    assumes them, so the default priority renders as an empty string. Raises
    PriorityError for an urgency out of range and TypeError for a wrong type.
    """
    if isinstance(urgency, bool) or not isinstance(urgency, int):
        raise TypeError(f"urgency must be an int, got {urgency!r}")
    if not isinstance(incremental, bool):
        raise TypeError(f"incremental must be a bool, got {incremental!r}")
    if not MIN_URGENCY <= urgency <= MAX_URGENCY:
        raise PriorityError(f"urgency {urgency} is outside 0..7")
    members = []
    if urgency != DEFAULT_URGENCY:
        members.append(f"u={urgency}")
    if incremental:
        members.append("i")
    return ", ".join(members)
