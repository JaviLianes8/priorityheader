"""Parse, merge and build the HTTP Priority field and PRIORITY_UPDATE frames (RFC 9218)."""

from __future__ import annotations

from ._build import build_params, build_priority
from ._errors import FrameError, PriorityError
from ._frames import (
    H2_FRAME_TYPE,
    H3_PUSH_FRAME_TYPE,
    H3_REQUEST_FRAME_TYPE,
    PriorityUpdate,
    decode_h2_update,
    decode_h3_update,
    encode_h2_update,
    encode_h3_update,
)
from ._model import (
    DEFAULT_URGENCY,
    MAX_URGENCY,
    MIN_URGENCY,
    ExtensionValue,
    Priority,
    PriorityParams,
)
from ._parse import FieldInput, merge_priority, parse_params, parse_priority
from ._sftypes import Date, DisplayString, Token

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_URGENCY",
    "H2_FRAME_TYPE",
    "H3_PUSH_FRAME_TYPE",
    "H3_REQUEST_FRAME_TYPE",
    "MAX_URGENCY",
    "MIN_URGENCY",
    "Date",
    "DisplayString",
    "ExtensionValue",
    "FieldInput",
    "FrameError",
    "Priority",
    "PriorityError",
    "PriorityParams",
    "PriorityUpdate",
    "Token",
    "build_params",
    "build_priority",
    "decode_h2_update",
    "decode_h3_update",
    "encode_h2_update",
    "encode_h3_update",
    "merge_priority",
    "parse_params",
    "parse_priority",
]
