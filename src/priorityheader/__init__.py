"""Parse and build the HTTP Priority header (RFC 9218), zero dependencies and typed."""

from __future__ import annotations

from ._build import build_priority
from ._errors import PriorityError
from ._model import Priority
from ._parse import parse_priority

__version__ = "0.1.0"

__all__ = ["Priority", "PriorityError", "build_priority", "parse_priority"]
