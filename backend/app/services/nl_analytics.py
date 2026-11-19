"""
Natural-language analytics (docs/SPEC.md §34).

Questions such as "What percentage of calls were positive this month?" are mapped to one
of a fixed set of analytics functions with validated parameters. The LLM never writes
SQL: it can only pick a function name and parameters from closed lists, and the answer
text is built from the query results, so the numbers can't be hallucinated.

Routing:
1. Keyword rules handle the common phrasings without an LLM call.
2. If the rules don't match but the question looks analytical ("how many", "percentage",
   "which ... highest"), a real LLM picks a function from the catalogue (validated).
3. Anything else returns None, and the caller answers with the search-based Copilot.

Every query is limited to what the user may see (``conversation_scope``).
"""

import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import conversation_scope, is_privileged
from app.core.logging import get_logger
from app.db.models import (
    ActionItem, AgentScore, Conversation, Entity, Objection, SalesInsight, SentimentResult, Summary, User,
)

logger = get_logger("services.nl_analytics")

MEETING_TYPES = ("internal_meeting", "client_meeting", "meeting")


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------

PERIODS = (
    "today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter",
    "this_year", "last_7_days", "last_30_days", "last_90_days", "last_365_days", "all_time",
)
DEFAULT_PERIOD = "last_30_days"


@dataclass
class Period:
    key: str
    label: str
    start: datetime | None
    end: datetime | None


def resolve_period(key: str, now: datetime | None = None, days: int | None = None) -> Period:
    """Date range (UTC, end exclusive) for a period key; ``days`` is used for "last N days"."""
    now = now or datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if days:
        return Period(f"last_{days}_days", f"the last {days} days", now - timedelta(days=days), None)
    if key == "today":
        return Period(key, "today", today, None)
    if key == "yesterday":
        return Period(key, "yesterday", today - timedelta(days=1), today)
    if key == "this_week":
        return Period(key, "this week", today - timedelta(days=today.weekday()), None)
    if key == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        return Period(key, "last week", start, start + timedelta(days=7))
    if key == "this_month":
        return Period(key, "this month", today.replace(day=1), None)
    if key == "last_month":
        first = today.replace(day=1)
        prev_last = first - timedelta(days=1)
        return Period(key, "last month", prev_last.replace(day=1), first)
    if key == "this_quarter":
        q_month = 3 * ((today.month - 1) // 3) + 1
        return Period(key, "this quarter", today.replace(month=q_month, day=1), None)
    if key == "this_year":
        return Period(key, "this year", today.replace(month=1, day=1), None)
    if key == "all_time":
        return Period(key, "all time", None, None)
    match = re.fullmatch(r"last_(\d+)_days", key)
    n = int(match.group(1)) if match else 30
    return Period(f"last_{n}_days", f"the last {n} days", now - timedelta(days=n), None)


_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}


def parse_period(text: str, now: datetime | None = None) -> Period:
    """Find a time expression in a question; defaults to the last 30 days."""
    t = text.lower()
    m = re.search(r"\b(?:last|past|previous)\s+(\d+)\s+(day|week|month|year)s?\b", t)
    if m:
        return resolve_period("", now, days=int(m.group(1)) * _UNIT_DAYS[m.group(2)])
    for pattern, key in (
        (r"\btoday\b", "today"),
        (r"\byesterday\b", "yesterday"),
        (r"\bthis week\b", "this_week"),
        (r"\b(?:last|previous|past) week\b", "last_week"),
        (r"\bthis month\b", "this_month"),
        (r"\b(?:last|previous) month\b", "last_month"),
        (r"\bpast month\b", "last_30_days"),
        (r"\bthis quarter\b", "this_quarter"),
        (r"\bthis year\b", "this_year"),
        (r"\b(?:past|last) year\b", "last_365_days"),
        (r"\b(?:all time|ever|overall|in total|so far)\b", "all_time"),
    ):
        if re.search(pattern, t):
            return resolve_period(key, now)
    return resolve_period(DEFAULT_PERIOD, now)


# ---------------------------------------------------------------------------
# Question parsing
# ---------------------------------------------------------------------------

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

_TYPE_PHRASES = (
    (r"\bsales\s+(?:calls?|conversations?|meetings?)\b", ("sales",)),
    (r"\bsupport\s+(?:calls?|conversations?|tickets?)\b", ("customer_support",)),
    (r"\bdemo(?:s|\s+calls?)?\b", ("product_demo",)),
    (r"\bfollow[- ]?up\s+(?:calls?|conversations?)\b", ("follow_up",)),
    (r"\bcomplaints?\b", ("complaint",)),
    (r"\bmeetings\b", MEETING_TYPES),
)

ANALYTIC_CUES = re.compile(
    r"\b(how many|number of|count|percent(?:age)?|ratio|share|average|avg|mean|total|most|least|"
    r"highest|lowest|best|worst|top|bottom|rank|leaderboard|breakdown|distribution|trend|compare|"
    r"frequent|frequently|common)\b|%"
)


def parse_types(text: str) -> tuple[str, ...] | None:
    t = text.lower()
    for pattern, types in _TYPE_PHRASES:
        if re.search(pattern, t):
            return types
    return None


def parse_limit(text: str, default: int = 5) -> int:
    t = text.lower()
    m = re.search(r"\btop\s+(\d+|" + "|".join(_NUMBER_WORDS) + r")\b", t)
    if not m:
        return default
    raw = m.group(1)
    return max(1, min(20, int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]))


@dataclass
class ToolCall:
    tool: str
    period: Period
    types: tuple[str, ...] | None = None
    limit: int = 5
    routed_by: str = "rules"


# (tool, pattern, needs an analytic cue)
_RULES: list[tuple[str, str, bool]] = [
    ("competitor_mentions", r"\bcompetitors?\b|\bcompetition\b", False),
    ("agent_leaderboard", r"\b(?:rep|reps|representative|representatives|agent|agents|salesperson|seller|performer)s?\b"
                          r".*\b(?:score|scores|scored|performance|perform|performed|best|worst|highest|lowest|top)\b"
                          r"|\b(?:highest|lowest|best|worst|top)\b.*\b(?:rep|representative|agent|salesperson|performer)\b"
                          r"|\bleaderboard\b|\bqa scores?\b|\bagent scores?\b", False),
    ("sentiment_breakdown", r"\bsentiment\b|\bpositive\b|\bnegative\b|\bhappy\b|\bunhappy\b|\bsatisf", True),
    ("top_objections", r"\bobjections?\b", True),
    ("high_intent_leads", r"\bhigh[- ]intent\b|\bhigh buying intent\b|\bhot leads?\b|\bhigh purchase intent\b", False),
    ("average_lead_score", r"\blead scores?\b", True),
    ("pipeline_stages", r"\bpipeline\b|\bstages?\b|\bdeals?\b.*\b(?:won|lost|stage)\b", True),
    ("open_action_items", r"\baction items?\b|\btasks?\b|\boverdue\b", True),
    ("top_topics", r"\btopics?\b|\bthemes?\b", True),
    ("conversation_volume", r"\b(?:calls?|conversations?|meetings?|recordings?)\b", True),
]


def route_by_rules(question: str, now: datetime | None = None) -> ToolCall | None:
    text = question.lower()
    has_cue = bool(ANALYTIC_CUES.search(text))
    for tool, pattern, needs_cue in _RULES:
        if re.search(pattern, text) and (has_cue or not needs_cue):
            return ToolCall(tool, parse_period(text, now), parse_types(text), parse_limit(text))
    return None


# ---------------------------------------------------------------------------
# LLM routing (validated; used only when the rules don't match an analytical question)
# ---------------------------------------------------------------------------

CONVERSATION_TYPES = (
    "sales", "customer_support", "product_demo", "follow_up", "internal_meeting",
    "client_meeting", "complaint", "general_business", "other",
)


class _RouterOutput(BaseModel):
    tool: str | None = None
    period: str | None = None
    conversation_type: str | None = None
    limit: int | None = None

    @field_validator("tool")
    @classmethod
    def _known_tool(cls, v):
        if v is not None and v not in TOOLS:
            raise ValueError("unknown tool")
        return v

    @field_validator("period")
    @classmethod
    def _known_period(cls, v):
        if v is not None and v not in PERIODS:
            raise ValueError("unknown period")
        return v

    @field_validator("conversation_type")
    @classmethod
    def _known_type(cls, v):
        if v is not None and v not in CONVERSATION_TYPES:
            raise ValueError("unknown conversation type")
        return v


async def route_with_llm(question: str, llm, now: datetime | None = None) -> ToolCall | None:
    from app.ai.providers.base import LLMMessage

    catalogue = "\n".join(f"- {name}: {tool.description}" for name, tool in TOOLS.items())
    system = (
        "You route business analytics questions to exactly one predefined function. You never write SQL.\n"
        f"Functions:\n{catalogue}\n\n"
        "Return JSON: {\"tool\": <function name or null>, \"period\": <one of "
        f"{', '.join(PERIODS)} or null>, \"conversation_type\": <one of {', '.join(CONVERSATION_TYPES)} or null>, "
        "\"limit\": <integer or null>}. Use null for tool when the question asks about the content of particular "
        "conversations or documents rather than counts, rankings, averages or percentages."
    )
    try:
        raw = await llm.complete_json(
            [LLMMessage(role="system", content=system), LLMMessage(role="user", content=question)],
            task="analytics_router",
        )
        parsed = _RouterOutput.model_validate(raw)
    except (ValidationError, Exception) as e:  # bad JSON, unknown names, provider errors
        logger.warning("Analytics routing by LLM failed", error=str(e))
        return None
    if not parsed.tool:
        return None
    period = resolve_period(parsed.period, now) if parsed.period else parse_period(question, now)
    types = (parsed.conversation_type,) if parsed.conversation_type else parse_types(question)
    limit = max(1, min(20, parsed.limit)) if parsed.limit else parse_limit(question)
    return ToolCall(parsed.tool, period, types, limit, routed_by="llm")


# ---------------------------------------------------------------------------
# Analytics functions
# ---------------------------------------------------------------------------

@dataclass
class AnalyticsResult:
    tool: str
    title: str
    answer: str
    period_label: str
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)

    def payload(self) -> dict:
        return {
            "tool": self.tool,
            "title": self.title,
            "period": self.period_label,
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass
class Tool:
    description: str
    run: Callable[[AsyncSession, Any, ToolCall], Awaitable[AnalyticsResult]]


def _scope(user, call: ToolCall) -> list:
    conds = conversation_scope(user)
    if call.period.start:
        conds.append(Conversation.created_at >= call.period.start)
    if call.period.end:
        conds.append(Conversation.created_at < call.period.end)
    if call.types:
        conds.append(Conversation.conversation_type.in_(call.types))
    return conds


def _noun(call: ToolCall, noun: str = "conversations") -> str:
    if call.types == MEETING_TYPES:
        return "meetings"
    if call.types:
        return f"{call.types[0].replace('_', ' ')} {noun}"
    return noun


def _when(call: ToolCall) -> str:
    """'this month', 'today', 'overall', or 'in the last 30 days'."""
    if call.period.key == "all_time":
        return "overall"
    if call.period.key.startswith(("this_", "last_week", "last_month")) or call.period.key in ("today", "yesterday"):
        return call.period.label
    return f"in {call.period.label}"


def _what(call: ToolCall, noun: str = "conversations") -> str:
    """'sales conversations in the last 30 days'"""
    return f"{_noun(call, noun)} {_when(call)}"


def _within(call: ToolCall) -> str:
    """'in the last 30 days', or 'in sales conversations this week' when filtered by type."""
    return f"in {_noun(call)} {_when(call)}" if call.types else _when(call)


def _pct(part: int, whole: int) -> str:
    return f"{round(part / whole * 100)}%" if whole else "0%"


async def _conversation_volume(db, user, call) -> AnalyticsResult:
    conds = _scope(user, call)
    rows = (await db.execute(
        select(Conversation.conversation_type, func.count(Conversation.id)).where(*conds).group_by(Conversation.conversation_type)
    )).all()
    total = sum(n for _, n in rows)
    meetings = sum(n for t, n in rows if t in MEETING_TYPES)
    answer = f"There were {total} {_what(call)}"
    if total and not call.types:
        answer += f": {total - meetings} calls and {meetings} meetings"
    return AnalyticsResult(
        "conversation_volume", "Conversations by type", answer + ".", call.period.label,
        ["Type", "Conversations"],
        [[t.replace("_", " "), n] for t, n in sorted(rows, key=lambda r: -r[1])],
    )


async def _sentiment_breakdown(db, user, call) -> AnalyticsResult:
    rows = dict((await db.execute(
        select(SentimentResult.overall_sentiment, func.count(SentimentResult.id))
        .join(Conversation, SentimentResult.conversation_id == Conversation.id)
        .where(*_scope(user, call)).group_by(SentimentResult.overall_sentiment)
    )).all())
    total = sum(rows.values())
    if not total:
        return AnalyticsResult("sentiment_breakdown", "Sentiment", f"No analyzed {_what(call)} have a sentiment score.",
                               call.period.label)
    ordered = [s for s in ("positive", "neutral", "mixed", "negative") if s in rows] + [s for s in rows if s not in ("positive", "neutral", "mixed", "negative")]
    answer = (
        f"{_pct(rows.get('positive', 0), total)} of the {total} {_what(call)} were positive"
        f" ({', '.join(f'{rows[s]} {s}' for s in ordered)})."
    )
    return AnalyticsResult(
        "sentiment_breakdown", "Sentiment breakdown", answer, call.period.label,
        ["Sentiment", "Conversations", "Share"], [[s, rows[s], _pct(rows[s], total)] for s in ordered],
    )


async def _top_objections(db, user, call) -> AnalyticsResult:
    rows = (await db.execute(
        select(
            Objection.category, func.count(Objection.id),
            func.sum(case((Objection.was_resolved.is_(True), 1), else_=0)),
        )
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*_scope(user, call)).group_by(Objection.category)
        .order_by(func.count(Objection.id).desc()).limit(call.limit)
    )).all()
    if not rows:
        return AnalyticsResult("top_objections", "Objections", f"No objections were recorded in {_what(call)}.", call.period.label)
    top, count, _ = rows[0]
    answer = f"The most frequent objection {_within(call)} was {top.replace('_', ' ')} ({count} times)."
    if len(rows) > 1:
        answer += " Next: " + ", ".join(f"{c.replace('_', ' ')} ({n})" for c, n, _ in rows[1:]) + "."
    return AnalyticsResult(
        "top_objections", f"Top {len(rows)} objections", answer, call.period.label,
        ["Objection", "Times raised", "Resolved on the call"],
        [[c.replace("_", " "), n, int(r or 0)] for c, n, r in rows],
    )


async def _agent_leaderboard(db, user, call) -> AnalyticsResult:
    rows = (await db.execute(
        select(User.full_name, func.avg(AgentScore.overall_score), func.count(AgentScore.id))
        .join(Conversation, AgentScore.conversation_id == Conversation.id)
        .join(User, Conversation.created_by == User.id)
        .where(*_scope(user, call), AgentScore.overall_score.is_not(None))
        .group_by(User.full_name).order_by(func.avg(AgentScore.overall_score).desc())
    )).all()
    if not rows:
        return AnalyticsResult("agent_leaderboard", "Agent scores", f"No scored {_what(call)}.", call.period.label)
    name, avg, n = rows[0]
    if is_privileged(user):
        answer = f"{name} had the highest average QA score {_within(call)}: {float(avg):.1f}/100 over {n} call(s)."
    else:
        answer = f"Your average QA score {_within(call)} is {float(avg):.1f}/100 over {n} call(s). Team rankings are visible to managers."
    answer += " Scores are AI-generated assessments."
    return AnalyticsResult(
        "agent_leaderboard", "Average QA score by person", answer, call.period.label,
        ["Person", "Average score", "Scored calls"], [[nm, round(float(a), 1), c] for nm, a, c in rows],
    )


async def _competitor_mentions(db, user, call) -> AnalyticsResult:
    rows = (await db.execute(
        select(Conversation.id, Conversation.title, Conversation.created_at, Entity.value)
        .join(Entity, Entity.conversation_id == Conversation.id)
        .where(*_scope(user, call), Entity.entity_type == "competitor")
        .order_by(Conversation.created_at.desc())
    )).all()
    grouped: dict[str, dict] = {}
    for conv_id, title, created, value in rows:
        entry = grouped.setdefault(conv_id, {"title": title, "date": created.date().isoformat(), "names": []})
        if value not in entry["names"]:
            entry["names"].append(value)
    if not grouped:
        return AnalyticsResult("competitor_mentions", "Competitor mentions", f"No competitors were mentioned in {_what(call)}.", call.period.label)
    names = sorted({n for e in grouped.values() for n in e["names"]})
    answer = (
        f"{len(grouped)} of the {_what(call)} mentioned a competitor ({', '.join(names)}): "
        + "; ".join(f"{e['title']} ({', '.join(e['names'])})" for e in list(grouped.values())[:5])
        + ("." if len(grouped) <= 5 else f"; and {len(grouped) - 5} more.")
    )
    return AnalyticsResult(
        "competitor_mentions", "Conversations mentioning competitors", answer, call.period.label,
        ["Conversation", "Date", "Competitors"],
        [[e["title"], e["date"], ", ".join(e["names"])] for e in grouped.values()],
    )


async def _high_intent_leads(db, user, call) -> AnalyticsResult:
    rows = (await db.execute(
        select(Conversation.title, SalesInsight.lead_score, SalesInsight.stage, Conversation.created_at)
        .join(SalesInsight, SalesInsight.conversation_id == Conversation.id)
        .where(*_scope(user, call), SalesInsight.purchase_intent == "high")
        .order_by(SalesInsight.lead_score.desc().nullslast())
    )).all()
    answer = f"There were {len(rows)} high-intent leads {_within(call)}"
    answer += (": " + ", ".join(f"{t} ({s})" for t, s, _, _ in rows[:5]) + ("." if len(rows) <= 5 else ", ...")) if rows else "."
    return AnalyticsResult(
        "high_intent_leads", "High-intent leads", answer, call.period.label,
        ["Conversation", "Lead score", "Stage", "Date"],
        [[t, s, (st or "-").replace("_", " "), c.date().isoformat()] for t, s, st, c in rows],
    )


async def _average_lead_score(db, user, call) -> AnalyticsResult:
    avg, n = (await db.execute(
        select(func.avg(SalesInsight.lead_score), func.count(SalesInsight.id))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*_scope(user, call), SalesInsight.lead_score.is_not(None))
    )).one()
    answer = (
        f"The average lead score across {n} scored {_what(call)} was {float(avg):.1f}/100."
        if n else f"No {_what(call)} have a lead score."
    )
    return AnalyticsResult("average_lead_score", "Average lead score", answer, call.period.label,
                           ["Scored conversations", "Average lead score"], [[n, round(float(avg), 1) if n else None]])


async def _pipeline_stages(db, user, call) -> AnalyticsResult:
    rows = dict((await db.execute(
        select(SalesInsight.stage, func.count(SalesInsight.id))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*_scope(user, call), SalesInsight.stage.is_not(None)).group_by(SalesInsight.stage)
    )).all())
    order = ("new", "contacted", "qualified", "demo", "proposal", "negotiation", "won", "lost")
    stages = [s for s in order if s in rows] + [s for s in rows if s not in order]
    total = sum(rows.values())
    answer = (
        f"{total} deals from {_what(call)} are in the pipeline: " + ", ".join(f"{rows[s]} {s}" for s in stages) + "."
        if total else f"No deals from {_what(call)} have a pipeline stage."
    )
    return AnalyticsResult("pipeline_stages", "Deals by pipeline stage", answer, call.period.label,
                           ["Stage", "Deals"], [[s, rows[s]] for s in stages])


async def _open_action_items(db, user, call) -> AnalyticsResult:
    from app.api.v1.action_items import visible_action_items

    now = datetime.utcnow()
    rows = (await db.execute(
        select(ActionItem.description, ActionItem.owner, ActionItem.priority, ActionItem.status, ActionItem.due_date_parsed)
        .outerjoin(Conversation, ActionItem.conversation_id == Conversation.id)
        .where(*visible_action_items(user), ActionItem.status.in_(("pending", "in_progress", "overdue")))
        .order_by(ActionItem.created_at.desc())
    )).all()
    overdue = sum(1 for *_, status, due in rows if status == "overdue" or (due and due < now))
    answer = f"There are {len(rows)} open action items ({overdue} overdue)."
    return AnalyticsResult(
        "open_action_items", "Open action items", answer, "current",
        ["Task", "Owner", "Priority", "Status"], [[d, o or "-", p, s.replace("_", " ")] for d, o, p, s, _ in rows[:20]],
    )


async def _top_topics(db, user, call) -> AnalyticsResult:
    from collections import Counter

    topics = (await db.execute(
        select(Summary.key_topics).join(Conversation, Summary.conversation_id == Conversation.id).where(*_scope(user, call))
    )).scalars().all()
    counter: Counter[str] = Counter()
    for items in topics:
        for item in items or []:
            if isinstance(item, str) and item.strip():
                counter[item.strip()] += 1
    top = counter.most_common(call.limit)
    answer = (
        f"The most discussed topics {_within(call)} were " + ", ".join(f"{t} ({n})" for t, n in top) + "."
        if top else f"No topics were recorded in {_what(call)}."
    )
    return AnalyticsResult("top_topics", "Most discussed topics", answer, call.period.label,
                           ["Topic", "Conversations"], [[t, n] for t, n in top])


TOOLS: dict[str, Tool] = {
    "conversation_volume": Tool("How many calls, meetings or conversations there were (optionally of one type)", _conversation_volume),
    "sentiment_breakdown": Tool("Share of conversations that were positive, neutral, mixed or negative", _sentiment_breakdown),
    "top_objections": Tool("Most frequent customer objections and how often they were resolved", _top_objections),
    "agent_leaderboard": Tool("Which sales or support representative had the highest average AI quality score", _agent_leaderboard),
    "competitor_mentions": Tool("Which conversations or customers mentioned competitors, and which ones", _competitor_mentions),
    "high_intent_leads": Tool("How many and which leads showed high purchase intent", _high_intent_leads),
    "average_lead_score": Tool("Average lead score of sales conversations", _average_lead_score),
    "pipeline_stages": Tool("How many deals are in each sales pipeline stage (won, lost, proposal, ...)", _pipeline_stages),
    "open_action_items": Tool("How many open and overdue action items (tasks) there are", _open_action_items),
    "top_topics": Tool("Most discussed topics across conversations", _top_topics),
}


async def answer_analytics_question(question: str, user, db: AsyncSession, llm=None) -> AnalyticsResult | None:
    """Answer with a predefined analytics function, or return None to fall back to the Copilot."""
    call = route_by_rules(question)
    if call is None and llm is not None and llm.provider_name != "mock" and ANALYTIC_CUES.search(question.lower()):
        call = await route_with_llm(question, llm)
    if call is None:
        return None
    logger.info("Analytics question routed", tool=call.tool, period=call.period.key, routed_by=call.routed_by)
    return await TOOLS[call.tool].run(db, user, call)
