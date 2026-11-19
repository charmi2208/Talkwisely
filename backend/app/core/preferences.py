"""
Per-user preferences (stored in ``User.preferences``) and their defaults.

Each preference changes real behavior:
- ``auto_action_items``: save the action items the AI extracts from your uploads.
- ``lead_intent_alerts``: notify you when one of your conversations scores 80+.
- ``pbx_auto_sync``: import new TalkWisely PBX calls into your organization on a schedule.
"""

from typing import Any

DEFAULT_PREFERENCES: dict[str, bool] = {
    "auto_action_items": True,
    "lead_intent_alerts": True,
    "pbx_auto_sync": False,
}

HIGH_INTENT_LEAD_SCORE = 80


def effective_preferences(stored: dict[str, Any] | None) -> dict[str, bool]:
    """Defaults overlaid with the user's saved values (unknown keys are dropped)."""
    prefs = dict(DEFAULT_PREFERENCES)
    for key, value in (stored or {}).items():
        if key in prefs and isinstance(value, bool):
            prefs[key] = value
    return prefs
