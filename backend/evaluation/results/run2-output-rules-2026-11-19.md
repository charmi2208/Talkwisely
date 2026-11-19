# TalkWiseAI agent evaluation

- Run: 2026-11-19 11:36 UTC
- Model: openai / openai/gpt-oss-120b
- Conversations: 6 (pipeline completed for 6)
- Mean pipeline time per conversation: 67.8 s

Small hand-labelled dataset; treat these numbers as indicative, not as a benchmark.

## Classification accuracy

| Task | Accuracy |
|---|---|
| conversation type | 100% |
| overall sentiment | 100% |
| primary intent | 100% |
| purchase intent | 50% |

## Extraction

| Task | Precision | Recall | F1 | TP / FP / FN |
|---|---|---|---|---|
| objection categories | 89% | 80% | 84% | 8 / 1 / 2 |
| competitors | 100% | 40% | 57% | 2 / 0 / 3 |
| action items | 71% | 91% | 80% | 10 / 4 / 1 |

## Summaries and output structure

- Key facts present in summaries (recall): 100%
- Agent responses valid against their schema without repair: 96% of 81

## Per conversation

| Conversation | Type | Sentiment | Intent | Purchase intent | Summary facts | Errors |
|---|---|---|---|---|---|---|
| Discovery call: 200-seat PBX migration | sales (ok) | positive (ok) | purchase_intent (ok) | high (ok) | 4/4 | 0 |
| Support: repeated dropped calls | complaint (ok) | mixed (ok) | complaint (ok) | none | 3/3 | 0 |
| Product demo: CRM integration and security questions | sales (ok) | mixed (ok) | demo_request (ok) | high (miss) | 3/3 | 0 |
| Internal meeting: Q3 support planning | internal_meeting (ok) | neutral (ok) | other (ok) | none | 3/3 | 0 |
| Follow-up: contract negotiation | sales (ok) | positive (ok) | purchase_intent (ok) | high (ok) | 3/3 | 0 |
| Cancellation request with retention offer | customer_support (ok) | mixed (ok) | cancellation (ok) | none (miss) | 3/3 | 0 |

## Summaries for human review

Score each 1-5 on the rubric in evaluation/README.md.

### Discovery call: 200-seat PBX migration

The customer, Dana from Northwind, is looking to replace their outdated on‑premise PBX for 200 staff with a reliable cloud phone system offering UK/US numbers and call recording. The sales rep offered a Business plan at $24 per seat annually, promised a written proposal by Friday, and a demo for the IT team next week.

### Support: repeated dropped calls

The customer reported repeated call drops affecting the Leeds office, causing lost sales. The support agent identified packet loss, escalated the issue to the network team, and promised a follow‑up call the next morning.

### Product demo: CRM integration and security questions

The sales rep demonstrated the call analytics dashboard and confirmed native Salesforce integration, UK data centre storage, and SOC 2 Type II compliance. The customer requested a two‑week free trial and the SOC 2 report for security review.

### Internal meeting: Q3 support planning

The team agreed to add a self‑service password reset page with a draft spec due by the 15th, assigned to Priya, and to hire an additional support agent for the evening shift. The job advert will be posted this week, and the question of extending weekend coverage will be revisited at next Tuesday's meeting.

### Follow-up: contract negotiation

The customer expressed interest but noted the competitor’s lower price and a budget timing constraint. The sales rep highlighted added value and proposed a July start to align with the budget, and the customer agreed to review a revised quote with finance.

### Cancellation request with retention offer

The customer requested cancellation of their account effective at the end of the month due to cost concerns. The support agent confirmed the cancellation for the 31st and will email a confirmation today.
