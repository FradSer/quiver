"""Shared helpers for parsing structured output from agent responses."""

from __future__ import annotations

import json
from typing import Any


class JsonExtractionError(ValueError):
    """Raised when an agent response contains no usable JSON object."""


def parse_json_object(raw: str) -> dict[str, Any]:
    """Pull the first complete JSON object out of an agent response."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise JsonExtractionError("response contains no JSON object")
    try:
        parsed: Any = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise JsonExtractionError(f"invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise JsonExtractionError("top-level JSON value is not an object")
    return parsed


def str_tuple(value: Any) -> tuple[str, ...]:
    """Coerce an arbitrary JSON value into a tuple of non-empty strings."""
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())
