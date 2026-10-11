"""The parsed Priority value and the defined urgency range."""

from __future__ import annotations

from typing import NamedTuple

MIN_URGENCY = 0
MAX_URGENCY = 7
DEFAULT_URGENCY = 3


class Priority(NamedTuple):
    """An HTTP Priority signal: an urgency 0..7 and an incremental flag."""

    urgency: int = DEFAULT_URGENCY
    incremental: bool = False
