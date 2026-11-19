"""
AI evaluation for the TalkWiseAI agents (docs/SPEC.md §62).

Runs the full LangGraph pipeline on the hand-labelled conversations in
``evaluation/dataset.json`` with the configured LLM provider and reports:

  accuracy    conversation type, overall sentiment, customer intent, purchase intent
  P / R / F1  objection categories, competitor mentions, action items
  recall      key facts that appear in the summary
  validity    share of agent responses that matched their JSON schema without repair

Summaries are also written out for human scoring (rubric in evaluation/README.md),
because automatic metrics can't judge whether a summary is faithful and useful.

Usage (from backend/):
    ./venv/bin/python -m evaluation.run_eval               # needs LLM_PROVIDER=openai
    ./venv/bin/python -m evaluation.run_eval --limit 2
    ./venv/bin/python -m evaluation.run_eval --allow-mock  # pipeline smoke test only
"""

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DATASET = HERE / "dataset.json"
RESULTS = HERE / "results"
SECONDS_PER_TURN = 6.0


# ---------------------------------------------------------------------------
# Metrics (pure functions; unit-tested in tests/unit/test_evaluation_metrics.py)
# ---------------------------------------------------------------------------

@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, tp: int, fp: int, fn: int) -> None:
        self.tp += tp
        self.fp += fp
        self.fn += fn

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or p + r == 0:
            return None if p is None or r is None else 0.0
        return 2 * p * r / (p + r)


def match_sets(predicted: list[str], expected: list[str], same=lambda a, b: a == b) -> tuple[int, int, int]:
    """(true positives, false positives, false negatives); each item matches at most once."""
    remaining = list(expected)
    tp = fp = 0
    for item in predicted:
        hit = next((e for e in remaining if same(item, e)), None)
        if hit is None:
            fp += 1
        else:
            tp += 1
            remaining.remove(hit)
    return tp, fp, len(remaining)


def names_match(predicted: str, expected: str) -> bool:
    """Competitor names: case-insensitive, either containing the other ("Zoom Phone" ~ "Zoom")."""
    a, b = predicted.strip().lower(), expected.strip().lower()
    return bool(a and b) and (a in b or b in a)


def has_keywords(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return all(k.lower() in lowered for k in keywords)


def match_keyword_items(predicted: list[str], expected: list[list[str]]) -> tuple[int, int, int]:
    """Action items: a predicted item matches an expected one when it contains all its keywords."""
    return match_sets(predicted, expected, same=lambda text, keywords: has_keywords(text, keywords))


def accuracy(results: list[bool]) -> float | None:
    return sum(results) / len(results) if results else None


# ---------------------------------------------------------------------------
# Running the pipeline
# ---------------------------------------------------------------------------

@dataclass
class ExampleResult:
    id: str
    title: str
    seconds: float
    status: str
    predicted: dict[str, Any]
    checks: dict[str, Any] = field(default_factory=dict)


def _segments(example: dict) -> list[dict]:
    return [
        {
            "speaker": speaker,
            "speaker_label": speaker,
            "start": i * SECONDS_PER_TURN,
            "end": (i + 1) * SECONDS_PER_TURN,
            "text": text,
            "confidence": None,
            "sequence_index": i,
        }
        for i, (speaker, text) in enumerate(example["segments"])
    ]


async def _run_example(example: dict, llm) -> ExampleResult:
    from app.ai.pipeline.graph import ConversationPipeline

    segments = _segments(example)
    started = time.perf_counter()
    state = await ConversationPipeline(llm).run(
        conversation_id=example["id"],
        organization_id="evaluation",
        raw_segments=segments,
        full_transcript_text=" ".join(s["text"] for s in segments),
        language="en",
        duration_seconds=len(segments) * SECONDS_PER_TURN,
    )
    summary_text = " ".join([
        state.get("executive_summary", ""), state.get("detailed_summary", ""), " ".join(state.get("key_topics", [])),
    ])
    predicted = {
        "conversation_type": state.get("conversation_type"),
        "overall_sentiment": state.get("overall_sentiment"),
        "primary_intent": state.get("primary_intent"),
        "purchase_intent": state.get("purchase_intent"),
        "objection_categories": sorted({o.get("category") for o in state.get("objections", []) if o.get("category")}),
        "competitors": [e["value"] for e in state.get("entities", []) if e.get("type") == "competitor"],
        "action_items": [a["description"] for a in state.get("action_items", [])],
        "executive_summary": state.get("executive_summary", ""),
        "summary_text": summary_text,
        "errors": state.get("errors", []),
    }
    return ExampleResult(example["id"], example["title"], time.perf_counter() - started, state["status"], predicted)


def score(examples: list[dict], results: list[ExampleResult]) -> dict[str, Any]:
    labels = {key: [] for key in ("conversation_type", "overall_sentiment", "primary_intent", "purchase_intent")}
    objections, competitors, actions = Counts(), Counts(), Counts()
    fact_hits = fact_total = 0

    for example, result in zip(examples, results):
        exp, pred = example["expected"], result.predicted
        for key in labels:
            if exp.get(key) is None:
                continue
            ok = pred.get(key) in exp[key]
            labels[key].append(ok)
            result.checks[key] = ok
        objections.add(*match_sets(pred["objection_categories"], exp["objection_categories"]))
        competitors.add(*match_sets(pred["competitors"], exp["competitors"], same=names_match))
        actions.add(*match_keyword_items(pred["action_items"], exp["action_items"]))
        hits = sum(has_keywords(pred["summary_text"], keywords) for keywords in exp["summary_facts"])
        result.checks["summary_facts"] = f"{hits}/{len(exp['summary_facts'])}"
        fact_hits += hits
        fact_total += len(exp["summary_facts"])

    return {
        "accuracy": {key: accuracy(values) for key, values in labels.items()},
        "extraction": {
            name: {"precision": c.precision, "recall": c.recall, "f1": c.f1, "tp": c.tp, "fp": c.fp, "fn": c.fn}
            for name, c in (("objection_categories", objections), ("competitors", competitors), ("action_items", actions))
        },
        "summary_fact_recall": fact_hits / fact_total if fact_total else None,
    }


async def evaluate(examples: list[dict], llm) -> dict[str, Any]:
    """Run every example and score it. Also measures structured output validity."""
    import app.ai.pipeline.nodes as nodes

    validity: list[tuple[str, int]] = []
    original = nodes.validate_output

    def recording_validate(task, raw):
        clean, issues = original(task, raw)
        validity.append((task, len(issues)))
        return clean, issues

    nodes.validate_output = recording_validate
    try:
        results = [await _run_example(example, llm) for example in examples]
    finally:
        nodes.validate_output = original

    metrics = score(examples, results)
    metrics["structured_output_validity"] = (
        sum(1 for _, n in validity if n == 0) / len(validity) if validity else None
    )
    metrics["agent_responses"] = len(validity)
    metrics["pipeline_completed"] = sum(r.status == "completed" for r in results)
    metrics["mean_seconds_per_conversation"] = sum(r.seconds for r in results) / len(results) if results else None
    return {"metrics": metrics, "results": results}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def to_markdown(run: dict[str, Any], provider: str, model: str) -> str:
    m = run["metrics"]
    lines = [
        "# TalkWiseAI agent evaluation",
        "",
        f"- Run: {datetime.utcnow():%Y-%m-%d %H:%M} UTC",
        f"- Model: {provider} / {model}",
        f"- Conversations: {len(run['results'])} (pipeline completed for {m['pipeline_completed']})",
        f"- Mean pipeline time per conversation: {m['mean_seconds_per_conversation']:.1f} s",
        "",
        "Small hand-labelled dataset; treat these numbers as indicative, not as a benchmark.",
        "",
        "## Classification accuracy",
        "",
        "| Task | Accuracy |",
        "|---|---|",
        *[f"| {k.replace('_', ' ')} | {_pct(v)} |" for k, v in m["accuracy"].items()],
        "",
        "## Extraction",
        "",
        "| Task | Precision | Recall | F1 | TP / FP / FN |",
        "|---|---|---|---|---|",
        *[
            f"| {k.replace('_', ' ')} | {_pct(v['precision'])} | {_pct(v['recall'])} | {_pct(v['f1'])} | {v['tp']} / {v['fp']} / {v['fn']} |"
            for k, v in m["extraction"].items()
        ],
        "",
        "## Summaries and output structure",
        "",
        f"- Key facts present in summaries (recall): {_pct(m['summary_fact_recall'])}",
        f"- Agent responses valid against their schema without repair: {_pct(m['structured_output_validity'])} "
        f"of {m['agent_responses']}",
        "",
        "## Per conversation",
        "",
        "| Conversation | Type | Sentiment | Intent | Purchase intent | Summary facts | Errors |",
        "|---|---|---|---|---|---|---|",
    ]

    def mark(result: ExampleResult, key: str) -> str:
        value = result.predicted.get(key) or "none"
        check = result.checks.get(key)
        return value if check is None else f"{value} ({'ok' if check else 'miss'})"

    for r in run["results"]:
        lines.append(
            f"| {r.title} | {mark(r, 'conversation_type')} | {mark(r, 'overall_sentiment')} | {mark(r, 'primary_intent')} | "
            f"{mark(r, 'purchase_intent')} | {r.checks.get('summary_facts')} | {len(r.predicted['errors'])} |"
        )
    lines += ["", "## Summaries for human review", "", "Score each 1-5 on the rubric in evaluation/README.md.", ""]
    for r in run["results"]:
        lines += [f"### {r.title}", "", r.predicted["executive_summary"] or "(empty)", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="Only run the first N conversations")
    parser.add_argument("--allow-mock", action="store_true", help="Run with the mock LLM (smoke test; scores are meaningless)")
    args = parser.parse_args()

    from app.ai.pipeline.graph import get_llm_provider
    from app.core.config import settings

    if settings.llm_provider == "mock" and not args.allow_mock:
        raise SystemExit(
            "LLM_PROVIDER is 'mock', which returns canned answers, so the scores would mean nothing.\n"
            "Configure a real model in backend/.env.local (see .env.local.example) or pass --allow-mock."
        )

    examples = json.loads(DATASET.read_text())["examples"][: args.limit]

    async def run():
        llm = get_llm_provider()
        try:
            return await evaluate(examples, llm)
        finally:
            close = getattr(llm, "aclose", None)
            if close:
                await close()

    result = asyncio.run(run())
    model = settings.llm_model if settings.llm_provider != "mock" else "canned responses"
    report = to_markdown(result, settings.llm_provider, model)

    RESULTS.mkdir(exist_ok=True)
    stem = "mock-smoke" if settings.llm_provider == "mock" else "latest"
    (RESULTS / f"{stem}.md").write_text(report)
    (RESULTS / f"{stem}.json").write_text(json.dumps({
        "model": f"{settings.llm_provider}/{model}",
        "run_at": datetime.utcnow().isoformat(),
        "metrics": result["metrics"],
        "predictions": {r.id: {k: v for k, v in r.predicted.items() if k != "summary_text"} for r in result["results"]},
    }, indent=2, default=str))
    print(report)
    print(f"\nSaved to {RESULTS / (stem + '.md')}")


if __name__ == "__main__":
    main()
