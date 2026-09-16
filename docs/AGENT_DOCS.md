# TalkWiseAI — AI Agent Architecture Documentation

TalkWiseAI orchestrates **17 specialized AI agents** using **LangGraph** to process business conversations.

---

## 1. Multi-Agent Inventory

| # | Agent Name | Role & Responsibility | Output Schema |
|---|------------|-----------------------|---------------|
| 1 | **Transcription Agent** | Cleans raw STT output, formats timestamps, labels speakers. | `raw_segments`, `speaker_map` |
| 2 | **Classification Agent** | Determines conversation type (sales, demo, support, client meeting). | `conversation_type`, `primary_purpose` |
| 3 | **Summarization Agent** | Generates executive summary, detailed summary, key topics, decisions. | `executive_summary`, `key_topics` |
| 4 | **Action Item Agent** | Extracts actionable tasks, owners, priorities, and due dates. | `action_items` |
| 5 | **Sentiment Agent** | Analyzes emotional tone, customer vs agent sentiment, and frustration markers. | `overall_sentiment`, `sentiment_trend` |
| 6 | **Customer Intent Agent** | Identifies primary intent (pricing inquiry, purchase intent, complaint). | `primary_intent`, `confidence` |
| 7 | **Pain Point Agent** | Maps operational/technical problems to customer needs & solutions. | `pain_points` |
| 8 | **Sales Intelligence Agent**| Calculates lead score (0-100), buying signals, deal health, budget range. | `lead_score`, `purchase_intent` |
| 9 | **Objection Agent** | Detects sales objections (price, timing, competition) & suggested responses.| `objections` |
| 10 | **Entity Agent** | Extracts competitors, products, technologies, and pricing mentions. | `entities` |
| 11 | **Meeting Minutes Agent** | Formats professional meeting minutes in Markdown. | `formatted_markdown`, `decisions` |
| 12 | **Email Generation Agent**| Generates context-aware follow-up email drafts based on call facts. | `subject`, `body` |
| 13 | **CRM Update Agent** | Proposes CRM field updates requiring human approval. | `proposed_changes` |
| 14 | **Recommendation Agent** | Recommends evidence-grounded next business actions. | `recommendations` |
| 15 | **QA Scoring Agent** | Evaluates sales/support representative performance metrics (0-100). | `overall_score`, `greeting_score` |
| 16 | **RAG Copilot Agent** | Grounded multi-tool conversational assistant across conversations & KB. | `answer`, `citations` |
| 17 | **Executive Report Agent**| Synthesizes organization analytics into management business reports. | `title`, `formatted_markdown` |

---

## 2. Safety & Groundedness Rules
1. **Fact vs Inference vs Recommendation**: Agents clearly distinguish between transcript facts, logical inferences, and suggested next steps.
2. **Anti-Hallucination Guard**: If information is absent from the transcript, agents output `null` or state "Not found in conversation" rather than inventing dates or prices.
