# AI agents

TalkWiseAI uses 17 specialized agents: 14 run in the LangGraph conversation pipeline for every upload, and 3 answer on demand. How they fit together is in `docs/AI_ARCHITECTURE.md`.

## Pipeline agents

Graph node names match `backend/app/ai/pipeline/graph.py`; each output is validated against the schema named in the last column (`backend/app/ai/schemas/agent_outputs.py`).

| # | Agent (graph node) | Stage | Produces | Schema |
|---|---|---|---|---|
| 1 | Transcript and speaker agent (`clean_transcript`) | sequential | Speaker labels; with a real LLM, a role per line (Sales Representative, Customer, ...) | - |
| 2 | Classification agent (`classify`) | sequential | Conversation type, purpose, business context, confidence | `ClassificationOutput` |
| 3 | Summarization agent (`summarize`) | parallel | Executive and detailed summary, key topics, decisions, important moments, open questions, next steps | `SummaryOutput` |
| 4 | Sentiment agent (`sentiment`) | parallel | Overall sentiment and score (-1 to 1), customer and agent sentiment, trend, timeline, frustration and satisfaction flags | `SentimentOutput` |
| 5 | Customer intent agent (`intent`) | parallel | Primary and secondary intents, confidence, evidence quotes | `IntentOutput` |
| 6 | Pain point agent (`pain_points`) | parallel | Problems with category, severity, desired outcome, evidence | `PainPointsOutput` |
| 7 | Sales intelligence agent (`sales_intelligence`) | parallel | Lead score (0-100), purchase intent, deal health, budget, decision maker, timeline, buying signals, pipeline stage, closing probability. Only runs for sales, demo, follow-up and client-meeting conversations. | `SalesOutput` |
| 8 | Objection agent (`objections`) | parallel | Objections with category, quote, timestamp, severity, whether resolved, suggested response | `ObjectionsOutput` |
| 9 | Entity agent (`entities`) | parallel | Competitors, products, companies, people, technologies, prices | `EntitiesOutput` |
| 10 | Action item agent (`action_items`) | parallel | Tasks with owner, due date, priority, timestamp | `ActionItemsOutput` |
| 11 | Meeting minutes agent (`meeting_minutes`) | sequential | Objective, participants, discussion points, decisions, action items, open questions, risks, next steps, next meeting, Markdown minutes | `MeetingMinutesOutput` |
| 12 | CRM update agent (`crm_update`) | sequential | Proposed field changes (`{field: {from, to}}`) waiting for human approval | `CRMUpdateOutput` |
| 13 | Recommendation agent (`recommendations`) | sequential | Next actions with reasoning, priority, urgency and evidence | `RecommendationsOutput` |
| 14 | QA agent (`agent_score`) | sequential | Overall and per-skill scores, talk ratio, strengths, weaknesses, coaching notes, AI-assessment disclaimer | `AgentScoreOutput` |

`validate_input` and `aggregate` are control nodes, not agents: the first stops runs with no speech, the second waits for all eight parallel agents.

## On-demand agents

| # | Agent | Endpoint | Produces |
|---|---|---|---|
| 15 | Copilot (RAG) | `POST /ai/copilot/chat` | Grounded answer with numbered citations to transcript passages, summaries or knowledge documents |
| 16 | Follow-up email agent | `POST /ai/generate-email` | Subject and body draft in the requested tone |
| 17 | Executive report agent | `POST /reports/generate` | Report summary, insights, risks and recommendations from computed metrics |

## Safety rules

1. **Grounded output.** Agents answer from the transcript, retrieved sources or supplied metrics only. Missing information is `null`, or "Not found in the available conversation(s)." in prose; never invented names, dates, prices, commitments or decisions.
2. **Fact, inference, recommendation.** The Copilot prefixes its own deductions with "Inference:" and advice with "Recommendation:"; recommendations carry their reasoning and evidence.
3. **Validated structure.** Every pipeline response is parsed into its schema before storage; repairs are logged and measured (`backend/evaluation`).
4. **Human in the loop.** CRM changes are proposals until a person approves them; emails are drafts.
5. **Labelled assessments.** QA scores always carry the AI-generated assessment disclaimer, in the API, the UI and reports.
6. **No generated SQL.** Natural-language analytics map to predefined queries.
7. **Mock mode is labelled.** Without an API key, canned results are used and the Copilot, email and report agents say they are in mock mode.
