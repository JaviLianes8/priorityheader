"""Read the HTTP Priority field into explicit parameters or a resolved Priority."""

from __future__ import annotations

from collections.abc import Sequence

from ._errors import PriorityError
from ._model import MAX_URGENCY, MIN_URGENCY, ExtensionValue, Priority, PriorityParams
from ._sfdict import parse_dictionary

#: What the parsers accept: one field value, its octets, the values of several field lines,
#: or None for an absent field.
FieldInput = str | bytes | bytearray | Sequence[str | bytes] | None


def field_text(header: object) -> str | None:
    """Return the field value to parse, joining several field lines with a comma."""
    if header is None:
        return None
    if isinstance(header, Sequence) and not isinstance(header, (str, bytes, bytearray)):
        return ", ".join(_line(line) for line in header)
    return _line(header)


def _line(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        # Latin-1 maps every octet to one character, so a non-ASCII octet reaches the
        # structured field reader and fails there with its offset.
        return bytes(value).decode("latin-1")
    raise TypeError(f"a Priority field is a str, bytes or a list of them, got {value!r}")


def parse_params(header: FieldInput, *, strict: bool = False) -> PriorityParams:
    """Return the members a Priority field carries, with None for each absent one.

    Use it for a response field, where an absent member means the server keeps the client
    value. The field is parsed as an RFC 9651 Dictionary. A field that fails to parse is
    ignored as a whole (every member None), or raises PriorityError with the offset when
    ``strict`` is true. Unknown members go to ``extensions``; a ``u`` that is not an
    Integer in 0..7 and an ``i`` that is not a Boolean are ignored in both modes, as RFC
    9218 section 4 requires. Several field lines are joined with ", " first, so offsets
    count in the joined text.
    """
    text = field_text(header)
    if text is None:
        return PriorityParams()
    try:
        members = parse_dictionary(text)
    except PriorityError:
        if strict:
            raise
        return PriorityParams()
    urgency: int | None = None
    incremental: bool | None = None
    extensions: dict[str, ExtensionValue] = {}
    for key, (value, _params) in members.items():
        if key == "u":
            urgency = _urgency(value)
        elif key == "i":
            incremental = value if isinstance(value, bool) else None
        elif isinstance(value, list):
            extensions[key] = tuple(item for item, _ in value)
        else:
            extensions[key] = value
    return PriorityParams(urgency, incremental, extensions)


def _urgency(value: object) -> int | None:
    if type(value) is not int:
        # bool and Date are int subclasses, and an inner list or Decimal is the wrong type.
        return None
    return value if MIN_URGENCY <= value <= MAX_URGENCY else None


def parse_priority(header: FieldInput, *, strict: bool = False) -> Priority:
    """Return the urgency and incremental flag a request Priority field asks for.

    Absent members take their defaults (urgency 3, not incremental), as they do in a
    request and in a PRIORITY_UPDATE frame. ``header`` is a field value, its octets, the
    values of several field lines, or None for an absent field. A field that fails to parse
    gives the defaults, or raises PriorityError when ``strict`` is true; see
    ``parse_params`` for the members that are ignored.
    """
    return parse_params(header, strict=strict).resolve()


def merge_priority(request: FieldInput, response: FieldInput) -> Priority:
    """Combine a request and a response Priority field as RFC 9218 section 8 describes.

    The request is resolved with the defaults, then every member the response carries
    replaces the client value; a member the response leaves out keeps the client value.
    Either field may be None when it is absent. Parsing is lenient on both sides.
    """
    return parse_params(response).over(parse_priority(request))
