# AI evaluation

Measures how well the TalkWiseAI agents analyze conversations (docs/SPEC.md §62).

## Dataset

`dataset.json` holds six short business conversations written for this project, each with expected labels:

| Conversation | What it tests |
|---|---|
| Discovery call: 200-seat PBX migration | Sales signals, price and competitor objections, high purchase intent |
| Support: repeated dropped calls | Frustrated customer, escalation, a competitor mentioned as a threat |
| Product demo: CRM integration and security | Integration and security objections, a competitor under evaluation |
| Internal meeting: Q3 support planning | Non-customer meeting: decisions, owners, no objections |
| Follow-up: contract negotiation | Price and timing objections, revised quote |
| Cancellation request with retention offer | Cancellation intent, low purchase intent |

The transcripts are synthetic. The labels were written and checked by the project team against each transcript; where more than one answer is defensible (for example "mixed" or "neutral" sentiment), all acceptable values are listed. Action items and summary facts are matched by keywords (for example, an action item matches `["call", "back"]` when its description contains both words).

## Metrics

| Metric | How it is computed |
|---|---|
| Accuracy | Conversation type, overall sentiment, primary intent, purchase intent: share of conversations whose prediction is an accepted label. Purchase intent is only scored where a label is given. |
| Precision, recall, F1 | Objection categories, competitor mentions (case-insensitive, either name containing the other) and action items, micro-averaged over all conversations. |
| Summary fact recall | Share of expected key facts found in the summary and key topics. |
| Structured output validity | Share of agent responses that matched their JSON schema without any repair (`app/ai/schemas/agent_outputs.py`). |

Generative quality can't be judged by keywords alone, so the report also prints each executive summary for human review.

### Human review rubric (score each summary 1-5)

| Score | Meaning |
|---|---|
| 5 | Accurate, complete, concise; nothing invented |
| 4 | Accurate; misses a minor point or is slightly wordy |
| 3 | Mostly accurate; misses an important point |
| 2 | Contains an error or an unsupported claim |
| 1 | Misleading or mostly wrong |

Score against four questions: Is every statement supported by the transcript? Are the customer's needs, decisions and next steps present? Are names, numbers and dates correct? Could a manager act on it without reading the transcript?

## Running it

From `backend/`, with a real model configured in `.env.local`:

```bash
./venv/bin/python -m evaluation.run_eval            # all conversations
./venv/bin/python -m evaluation.run_eval --limit 2  # quick check
```

Results are written to `results/latest.md` and `results/latest.json`. With `LLM_PROVIDER=mock` the runner refuses to score (canned answers would make the numbers meaningless); `--allow-mock` runs it as a pipeline smoke test into `results/mock-smoke.*`. The unit test `tests/unit/test_evaluation_metrics.py` covers the metric functions.

## Results

Model: Groq `openai/gpt-oss-120b`, 6 conversations, 13 agent responses each.

| Metric | Run 1 (baseline) | Run 2 (timestamps as seconds) | Run 3 (competitor defined) |
|---|---|---|---|
| Conversation type accuracy | 100% | 100% | 100% |
| Overall sentiment accuracy | 100% | 100% | 83% |
| Primary intent accuracy | 100% | 100% | 100% |
| Purchase intent accuracy | 50% | 50% | 50% |
| Objection categories F1 | 74% | 84% | 84% |
| Competitor mentions F1 | 75% | 57% | 89% |
| Action items F1 | 77% | 80% | 80% |
| Summary fact recall | 95% | 100% | 100% |
| Valid without repair | 53% | 96% | 96% |
| Mean seconds per conversation | 63.9 | 67.8 | 68.0 |

What changed between runs:

- **Run 1 to 2:** almost every repair in run 1 was a timestamp returned as text ("00:06"), copied from the `[mm:ss]` transcript format. All prompts now end with shared output rules that ask for seconds and for `null` instead of guesses. Validity rose from 53% to 96%.
- **Run 2 to 3:** competitors such as Zoom Phone and 8x8 were tagged as plain companies. The entity prompt now defines a competitor as a company selling a similar product that the customer uses, evaluates, got a quote from or is switching to.

Known weaknesses:

- **Purchase intent** is the weakest task. The demo call was scored "high" where the label is "medium", and the cancellation call got no score because the sales agent only runs for sales-type conversations (by design).
- **Sentiment** on the discovery call came back "mixed" in run 3 versus "positive" in earlier runs. With six conversations, one call changes accuracy by 17 points, so run-to-run variation is large.

Per-run reports: `results/baseline-2026-11-19.md`, `results/run2-output-rules-2026-11-19.md`, `results/run3-competitor-definition-2026-11-19.md` (also `latest.md`).
