"""Helpers for decoding page.evaluate JSON payloads across backends."""

from __future__ import annotations

import json
from typing import Any


_JSON_NATIVE_TYPES = (dict, list, int, float, bool, type(None))


def decode_page_json(value: Any) -> Any:
    """Normalize page.evaluate JSON results across CDP and agent-browser backends.

    CDP paths typically return JSON strings, while agent-browser may already coerce
    JSON output into native Python objects. This helper accepts both forms.
    """
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, _JSON_NATIVE_TYPES):
        return value
    raise TypeError(f"unsupported page JSON payload type: {type(value).__name__}")
