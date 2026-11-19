"""
Structured output schemas for the pipeline agents.

Every agent returns JSON, but models still drift: "85/100" for an integer score,
"01:23" for a timestamp, "High" for an enum, a sentence where a list belongs, or
"Not mentioned" where the value is simply unknown. ``validate_output`` parses the raw
JSON into the agent's schema, repairs what it safely can, and reports each repair
as an issue. Pipeline nodes only ever see the cleaned dict.

The issue list doubles as a reliability metric: ``tests/evaluation`` reports the share
of responses that needed no repair ("structured output validity").

Unknown values become null rather than guesses (docs/SPEC.md §53).
"""

from contextvars import ContextVar
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError

from app.db.sanitize import to_bool, to_float, to_int

MAX_ITEMS = 50
AI_DISCLAIMER = "This is an AI-generated assessment and should be used as one input among many."

CONVERSATION_TYPES = (
    "sales", "customer_support", "product_demo", "follow_up", "internal_meeting",
    "client_meeting", "complaint", "general_business", "other",
)
INTENTS = (
    "product_inquiry", "pricing_inquiry", "demo_request", "purchase_intent", "support_request", "complaint",
    "cancellation", "upgrade", "integration_request", "feature_request", "information_request", "other",
)
SENTIMENTS = ("positive", "negative", "neutral", "mixed")
PRIORITIES = ("low", "medium", "high", "urgent")
SEVERITIES = ("low", "medium", "high")
PIPELINE_STAGES = ("new", "contacted", "qualified", "demo", "proposal", "negotiation", "won", "lost")
OBJECTION_CATEGORIES = (
    "price", "features", "security", "integration", "competitor", "timing", "contract",
    "complexity", "trust", "implementation", "support", "other",
)
ENTITY_TYPES = ("competitor", "product", "company", "person", "technology", "location", "price", "plan", "feature", "other")
PAIN_CATEGORIES = ("operational", "technical", "financial", "process", "other")
URGENCIES = ("today", "this_week", "this_month", "before_demo", "other")
CRM_ENTITIES = ("lead", "contact", "opportunity", "deal")

# Phrases models use for "unknown"; stored as null so the UI can say "Not found"
_UNKNOWN = {
    "", "null", "none", "n/a", "na", "unknown", "not specified", "not mentioned", "not discussed",
    "not found", "not available", "not provided", "not stated", "tbd", "-",
}

_issues: ContextVar[list[str] | None] = ContextVar("agent_output_issues", default=None)


def _note(message: str) -> None:
    issues = _issues.get()
    if issues is not None:
        issues.append(message)


# ---------------------------------------------------------------------------
# Lenient field types
# ---------------------------------------------------------------------------

def _is_unknown(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower().rstrip(".")
        return text in _UNKNOWN or text.startswith("not found in the available conversation")
    return False


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        _note("expected text, got a list")
        return "; ".join(str(v) for v in value)
    if not isinstance(value, str):
        return str(value)
    return value.strip()


def _opt_text(value: Any) -> str | None:
    if _is_unknown(value):
        return None
    return _text(value)[:1000] or None


def _seconds(value: Any) -> float | None:
    if _is_unknown(value):
        return None
    parsed = to_float(value)
    if parsed is None:
        _note(f"unreadable timestamp {value!r}")
    elif not isinstance(value, (int, float)):
        _note(f"timestamp given as text {value!r}")
    return parsed if parsed is None or parsed >= 0 else None


def _clamped(lo: float, hi: float, as_int: bool = False):
    def parse(value: Any):
        if _is_unknown(value):
            return None
        parsed = to_int(value) if as_int else to_float(value)
        if parsed is None:
            _note(f"unreadable number {value!r}")
            return None
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            _note(f"number given as text {value!r}")
        if not as_int and hi == 1 and 1 < parsed <= 100:  # 80 meaning 80%
            _note(f"percentage {value!r} where a 0-1 value was expected")
            parsed = parsed / 100
        if parsed < lo or parsed > hi:
            _note(f"{value!r} outside {lo}..{hi}")
            parsed = max(lo, min(hi, parsed))
        return parsed
    return parse


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        if value is not None:
            _note(f"boolean given as {value!r}")
    return to_bool(value) if value is not None else False


def _count(value: Any) -> int | None:
    if _is_unknown(value):
        return None
    parsed = to_int(value)
    return max(0, parsed) if parsed is not None else None


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if _is_unknown(value):
            return []
        _note("expected a list, got text")
        return [value.strip()]
    if not isinstance(value, list):
        _note(f"expected a list, got {type(value).__name__}")
        return []
    items = []
    for item in value[:MAX_ITEMS]:
        if isinstance(item, dict):
            item = item.get("text") or item.get("description") or item.get("decision") or item.get("value") or ""
        text = str(item).strip()
        if text and not _is_unknown(text):
            items.append(text)
    return items


def _list_of(value: Any) -> list:
    """Lists of objects: drop non-objects, cap the length."""
    if value is None:
        return []
    if isinstance(value, dict):
        _note("expected a list, got a single object")
        value = [value]
    if not isinstance(value, list):
        _note(f"expected a list, got {type(value).__name__}")
        return []
    kept = [item for item in value if isinstance(item, dict)]
    if len(kept) != len(value):
        _note("list contained non-object items")
    return kept[:MAX_ITEMS]


def choice(allowed: tuple[str, ...], default: str | None):
    """Enum-like text: lowercased snake_case; anything else becomes ``default``."""
    def parse(value: Any) -> str | None:
        if _is_unknown(value):
            return default
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if text in allowed:
            if text != value:
                _note(f"enum {value!r} needed normalizing")
            return text
        _note(f"{value!r} is not one of {', '.join(allowed)}")
        return default
    return BeforeValidator(parse)


Text = Annotated[str, BeforeValidator(_text)]
OptText = Annotated[str | None, BeforeValidator(_opt_text)]
Seconds = Annotated[float | None, BeforeValidator(_seconds)]
Score100 = Annotated[int | None, BeforeValidator(_clamped(0, 100, as_int=True))]
Unit = Annotated[float | None, BeforeValidator(_clamped(0, 1))]
Signed = Annotated[float | None, BeforeValidator(_clamped(-1, 1))]
Bool = Annotated[bool, BeforeValidator(_bool)]
Count = Annotated[int | None, BeforeValidator(_count)]
StrList = Annotated[list[str], BeforeValidator(_str_list)]


def ObjList(model):  # noqa: N802 - reads like a type
    return Annotated[list[model], BeforeValidator(_list_of)]


class _Schema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    REQUIRED: ClassVar[tuple[str, ...]] = ()  # missing keys are reported as issues


class Moment(_Schema):
    timestamp: Seconds = None
    description: Text = ""


class EvidenceQuote(_Schema):
    text: Text = ""
    timestamp: Seconds = None


# ---------------------------------------------------------------------------
# Agent schemas
# ---------------------------------------------------------------------------

class ClassificationOutput(_Schema):
    REQUIRED = ("conversation_type",)
    conversation_type: Annotated[str, choice(CONVERSATION_TYPES, "other")] = "other"
    primary_purpose: Text = ""
    business_context: Text = ""
    confidence: Unit = None


class SummaryOutput(_Schema):
    REQUIRED = ("executive_summary",)
    executive_summary: Text = ""
    detailed_summary: Text = ""
    key_topics: StrList = []
    decisions: StrList = []
    important_moments: ObjList(Moment) = []
    open_questions: StrList = []
    next_steps: StrList = []


class ActionItemOut(_Schema):
    description: Text = ""
    owner: OptText = None
    owner_speaker: OptText = None
    due_date: OptText = None
    priority: Annotated[str, choice(PRIORITIES, "medium")] = "medium"
    related_topic: OptText = None
    timestamp: Seconds = None


class ActionItemsOutput(_Schema):
    REQUIRED = ("action_items",)
    action_items: ObjList(ActionItemOut) = []


# Overall sentiment is an enum; per-speaker and timeline labels are free text
# ("interested", "mostly positive") because the prompt asks for a description there.
Label = Annotated[str | None, BeforeValidator(lambda v: (_opt_text(v) or "").lower()[:20] or None)]


class SentimentPoint(_Schema):
    timestamp: Seconds = None
    speaker: OptText = None
    sentiment: Label = None
    score: Signed = None


class SentimentOutput(_Schema):
    REQUIRED = ("overall_sentiment",)
    overall_sentiment: Annotated[str, choice(SENTIMENTS, "neutral")] = "neutral"
    overall_score: Signed = None
    customer_sentiment: Label = None
    agent_sentiment: Label = None
    sentiment_trend: Text = ""
    timeline: ObjList(SentimentPoint) = []
    positive_moments: ObjList(Moment) = []
    negative_moments: ObjList(Moment) = []
    frustration_detected: Bool = False
    satisfaction_detected: Bool = False


class IntentOutput(_Schema):
    REQUIRED = ("primary_intent",)
    primary_intent: Annotated[str, choice(INTENTS, "other")] = "other"
    secondary_intents: StrList = []
    confidence: Unit = None
    evidence: ObjList(EvidenceQuote) = []


class PainPointOut(_Schema):
    category: Annotated[str, choice(PAIN_CATEGORIES, "other")] = "other"
    description: Text = ""
    severity: Annotated[str, choice(SEVERITIES, "medium")] = "medium"
    desired_outcome: OptText = None
    potential_solution: OptText = None
    evidence: OptText = None
    timestamp: Seconds = None


class PainPointsOutput(_Schema):
    REQUIRED = ("pain_points",)
    pain_points: ObjList(PainPointOut) = []


class BuyingSignal(_Schema):
    signal: Text = ""
    timestamp: Seconds = None
    evidence: OptText = None


class SalesOutput(_Schema):
    REQUIRED = ("lead_score", "purchase_intent")
    lead_score: Score100 = None
    purchase_intent: Annotated[str | None, choice(SEVERITIES, None)] = None
    deal_health: Annotated[str | None, choice(("healthy", "at_risk", "critical"), None)] = None
    budget_discussed: Bool = False
    budget_range: OptText = None
    decision_maker_present: Bool = False
    timeline_discussed: Bool = False
    timeline: OptText = None
    buying_signals: ObjList(BuyingSignal) = []
    upsell_opportunities: StrList = []
    cross_sell_opportunities: StrList = []
    stage: Annotated[str | None, choice(PIPELINE_STAGES, None)] = None
    closing_probability: Unit = None


class ObjectionOut(_Schema):
    category: Annotated[str, choice(OBJECTION_CATEGORIES, "other")] = "other"
    description: Text = ""
    exact_quote: OptText = None
    timestamp: Seconds = None
    severity: Annotated[str, choice(SEVERITIES, "medium")] = "medium"
    was_resolved: Bool = False
    suggested_response: OptText = None


class ObjectionsOutput(_Schema):
    REQUIRED = ("objections",)
    objections: ObjList(ObjectionOut) = []


class EntityOut(_Schema):
    type: Annotated[str, choice(ENTITY_TYPES, "other")] = "other"
    value: Text = ""
    context: OptText = None
    timestamp: Seconds = None
    sentiment: Label = None
    mention_count: Count = 1


class EntitiesOutput(_Schema):
    REQUIRED = ("entities",)
    entities: ObjList(EntityOut) = []


class MeetingMinutesOutput(_Schema):
    REQUIRED = ("objective", "discussion_points")
    objective: OptText = None
    participants_summary: OptText = None
    discussion_points: StrList = []
    decisions: StrList = []
    action_items_summary: StrList = []
    open_questions: StrList = []
    risks: StrList = []
    next_steps: StrList = []
    next_meeting: OptText = None


class RecommendationOut(_Schema):
    category: Text = "other"
    action: Text = ""
    reasoning: OptText = None
    priority: Annotated[str, choice(PRIORITIES, "medium")] = "medium"
    urgency: Annotated[str, choice(URGENCIES, "other")] = "other"
    evidence: StrList = []


class RecommendationsOutput(_Schema):
    REQUIRED = ("recommendations",)
    recommendations: ObjList(RecommendationOut) = []


def _changes(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        if value is not None:
            _note("proposed_changes is not an object")
        return {}
    changes = {}
    for field, change in list(value.items())[:MAX_ITEMS]:
        if isinstance(change, dict) and "to" in change:
            changes[str(field)] = {"from": change.get("from"), "to": change.get("to")}
        else:
            _note(f"change for {field!r} lacks from/to")
            changes[str(field)] = {"from": None, "to": change}
    return {k: v for k, v in changes.items() if not _is_unknown(v["to"])}


class CRMUpdateOutput(_Schema):
    REQUIRED = ("proposed_changes",)
    crm_entity_type: Annotated[str, choice(CRM_ENTITIES, "lead")] = "lead"
    proposed_changes: Annotated[dict[str, dict[str, Any]], BeforeValidator(_changes)] = {}
    reasoning: OptText = None


def _disclaimer(value: Any) -> str:
    text = _text(value)
    if "ai-generated" not in text.lower():
        if text:
            _note("disclaimer did not say the assessment is AI-generated")
        return AI_DISCLAIMER
    return text


class AgentScoreOutput(_Schema):
    REQUIRED = ("overall_score",)
    overall_score: Score100 = None
    greeting_score: Score100 = None
    professionalism_score: Score100 = None
    empathy_score: Score100 = None
    listening_score: Score100 = None
    question_quality_score: Score100 = None
    product_knowledge_score: Score100 = None
    objection_handling_score: Score100 = None
    closing_score: Score100 = None
    talk_ratio: Unit = None
    interruption_count: Count = None
    filler_word_count: Count = None
    strengths: StrList = []
    weaknesses: StrList = []
    improvement_suggestions: StrList = []
    coaching_notes: OptText = None
    disclaimer: Annotated[str, BeforeValidator(_disclaimer)] = AI_DISCLAIMER


SCHEMAS: dict[str, type[_Schema]] = {
    "classification": ClassificationOutput,
    "summarization": SummaryOutput,
    "action_items": ActionItemsOutput,
    "sentiment": SentimentOutput,
    "intent": IntentOutput,
    "pain_points": PainPointsOutput,
    "sales_intelligence": SalesOutput,
    "objections": ObjectionsOutput,
    "entities": EntitiesOutput,
    "meeting_minutes": MeetingMinutesOutput,
    "recommendations": RecommendationsOutput,
    "crm_update": CRMUpdateOutput,
    "agent_score": AgentScoreOutput,
}

# List items that carry no content are dropped after validation
_ITEM_CONTENT = {
    "action_items": "description",
    "pain_points": "description",
    "objections": "description",
    "entities": "value",
    "recommendations": "action",
}


def validate_output(task: str, raw: Any) -> tuple[dict, list[str]]:
    """Parse ``raw`` agent JSON into the task's schema.

    Returns ``(clean, issues)``. ``clean`` always has every schema field (defaults for
    anything missing or unusable); ``issues`` lists what had to be repaired. Tasks
    without a schema pass through unchanged.
    """
    schema = SCHEMAS.get(task)
    if schema is None:
        return (raw if isinstance(raw, dict) else {}), []

    issues: list[str] = []
    token = _issues.set(issues)
    try:
        if not isinstance(raw, dict):
            issues.append(f"response is {type(raw).__name__}, not an object")
            raw = {}
        if not raw:
            issues.append("empty response")
        for field in schema.REQUIRED:
            if field not in raw:
                issues.append(f"missing required field {field!r}")
        try:
            clean = schema.model_validate(raw).model_dump()
        except ValidationError as e:
            issues.append(f"schema validation failed: {e.error_count()} error(s)")
            clean = schema().model_dump()
    finally:
        _issues.reset(token)

    for field, key in _ITEM_CONTENT.items():
        if field in clean:
            clean[field] = [item for item in clean[field] if item.get(key)]
    return clean, issues
