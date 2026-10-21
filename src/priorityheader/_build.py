"""Render priority parameters into a Priority field value."""

from __future__ import annotations

from collections.abc import Mapping

from ._errors import shown
from ._model import (
    DEFAULT_INCREMENTAL,
    DEFAULT_URGENCY,
    ExtensionValue,
    PriorityParams,
    check_extensions,
    check_incremental,
    check_urgency,
)
from ._sfwrite import serialize_dictionary


def build_priority(
    urgency: int = DEFAULT_URGENCY,
    incremental: bool = DEFAULT_INCREMENTAL,
    *,
    extensions: Mapping[str, ExtensionValue] | None = None,
) -> str:
    """Render a request Priority field value, dropping anything left at its default.

    ``urgency`` must be an integer in 0..7 and ``incremental`` a boolean. A peer reading a
    request or a PRIORITY_UPDATE frame assumes urgency 3 and a false incremental flag, so
    they are omitted and the default priority renders as an empty string (send no field).
    ``extensions`` adds further members (RFC 9218 section 4.3) after ``u`` and ``i``.
    Raises PriorityError for a value out of range or a key that is not a structured field
    key, and TypeError for a wrong type.

    >>> from priorityheader import Token, build_priority
    >>> build_priority()
    ''
    >>> build_priority(0, True)
    'u=0, i'
    >>> build_priority(1, extensions={"hint": Token("viewport")})
    'u=1, hint=viewport'
    """
    urgency = check_urgency(urgency)
    check_incremental(incremental)
    return _render(
        None if urgency == DEFAULT_URGENCY else urgency,
        True if incremental else None,
        check_extensions(extensions or {}),
    )


def build_params(params: PriorityParams) -> str:
    """Render exactly the members ``params`` carries, defaults included.

    Use it for a response, where an absent member means "keep the client value" and so
    ``u=3`` has to be written to move a client back to the default urgency. A false
    incremental flag is written as ``i=?0``. TypeError when ``params`` is not a
    PriorityParams.

    >>> from priorityheader import PriorityParams, build_params
    >>> build_params(PriorityParams(urgency=3, incremental=False))
    'u=3, i=?0'
    >>> build_params(PriorityParams())
    ''
    """
    if not isinstance(params, PriorityParams):
        raise TypeError(f"params must be PriorityParams, got {shown(params)}")
    return _render(params.urgency, params.incremental, dict(params.extensions))


def _render(
    urgency: int | None, incremental: bool | None, extensions: dict[str, ExtensionValue]
) -> str:
    members: list[tuple[str, object]] = []
    if urgency is not None:
        members.append(("u", urgency))
    if incremental is not None:
        members.append(("i", incremental))
    members.extend(extensions.items())
    return serialize_dictionary(members)
