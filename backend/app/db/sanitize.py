"""
Coerce AI-produced values to the column types they're stored in.

LLMs return "00:48" where a float timestamp is expected, "85/100" for an
integer score, "High" for an enum, or a list where text belongs. clean_row()
fixes those in place so a single odd value can't fail the whole insert.
"""

import json
import re
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text

# Enum-like columns compared in lowercase snake_case elsewhere in the app
ENUM_COLUMNS = {
    "priority", "severity", "purchase_intent", "deal_health", "overall_sentiment",
    "customer_sentiment", "agent_sentiment", "sentiment", "entity_type", "conversation_type",
    "urgency", "stage", "crm_entity_type", "category", "primary_intent",
}

_CLOCK = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)$")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def to_float(value: Any) -> float | None:
    """Numbers, numeric strings, 'mm:ss' / 'hh:mm:ss' clock times and percentages."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if clock := _CLOCK.match(text):
        hours, minutes, seconds = clock.groups()
        return int(hours or 0) * 3600 + int(minutes) * 60 + float(seconds)
    number = _NUMBER.search(text)
    if not number:
        return None
    parsed = float(number.group())
    return parsed / 100 if text.endswith("%") else parsed


def to_int(value: Any) -> int | None:
    if isinstance(value, str) and "/" in value:  # "85/100"
        value = value.split("/", 1)[0]
    parsed = to_float(value)
    return int(round(parsed)) if parsed is not None else None


def to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def to_text(value: Any, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return value[:max_length] if max_length else value


def clean_row(obj: Any) -> Any:
    """Coerce every column value on an ORM object to its declared type. Returns the object."""
    for column in obj.__table__.columns:
        key = column.key
        if key not in obj.__dict__:
            continue  # never assigned: leave it to the column default
        value = obj.__dict__[key]
        col_type = column.type

        if isinstance(col_type, Boolean):
            value = to_bool(value) if value is not None else None
        elif isinstance(col_type, Integer):
            value = to_int(value)
        elif isinstance(col_type, Float):
            value = to_float(value)
        elif isinstance(col_type, (String, Text)):
            value = to_text(value, getattr(col_type, "length", None))
            if value is not None and key in ENUM_COLUMNS:
                value = value.strip().lower().replace(" ", "_").replace("-", "_")[: getattr(col_type, "length", None)]

        if value is None and not column.nullable and not column.primary_key:
            if column.default is not None and column.default.is_scalar:
                value = column.default.arg
            elif isinstance(col_type, (String, Text)):
                value = ""
            elif isinstance(col_type, (Integer, Float)):
                value = 0

        setattr(obj, key, value)
    return obj
