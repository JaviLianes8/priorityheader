"""Parse, merge and build the HTTP Priority field and PRIORITY_UPDATE frames (RFC 9218).

>>> import priorityheader as ph
>>> ph.MIN_URGENCY, ph.DEFAULT_URGENCY, ph.MAX_URGENCY
(0, 3, 7)
>>> hex(ph.H2_FRAME_TYPE), hex(ph.H3_REQUEST_FRAME_TYPE), hex(ph.H3_PUSH_FRAME_TYPE)
('0x10', '0xf0700', '0xf0701')
>>> value: ph.ExtensionValue = (1, ph.Token("a"))
>>> lines: ph.FieldInput = ["u=1", b"i"]
>>> ph.build_priority(extensions={"x": value}), ph.parse_priority(lines)
('x=(1 a)', Priority(urgency=1, incremental=True))
"""

from __future__ import annotations

from ._build import build_params, build_priority
from ._errors import FrameError, PriorityError
from ._frames import H2_FRAME_TYPE, H3_PUSH_FRAME_TYPE, H3_REQUEST_FRAME_TYPE, PriorityUpdate
from ._h2 import decode_h2_update, encode_h2_update
from ._h3 import decode_h3_update, encode_h3_update
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

__version__ = "1.0.0"

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
