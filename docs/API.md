# API reference

Generated from the FastAPI routes by `backend/scripts/generate_docs.py`; don't edit by hand.
Interactive docs with request and response schemas: http://localhost:8000/api/docs

All paths start with `/api/v1`. Every endpoint except the public auth ones needs
`Authorization: Bearer <access token>` (from `POST /auth/login`).

**Who can call it**
- *Signed in*: any active user. Data is still limited to what the user may see: agents only get
  conversations they uploaded (and anything derived from them); admins and managers see the whole
  organization. Every query is scoped to the user's organization.
- *admin*, *manager*: only those roles; others get 403.

Errors use FastAPI's format: `{"detail": "message"}` (or a list of validation issues for 422).
Rate limits: 10 requests per minute per IP on login, register and password reset; 
`RATE_LIMIT_REQUESTS` per `RATE_LIMIT_PERIOD_SECONDS` on everything else (429 with `Retry-After`).

## Authentication

| Method | Path | Who | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a new user and organization. |
| POST | `/auth/login` | Public | Authenticate user and return JWT tokens. |
| POST | `/auth/refresh` | Public | Exchange a refresh token for new access + refresh tokens. |
| GET | `/auth/me` | Signed in | Return the authenticated user's profile. |
| POST | `/auth/forgot-password` | Public | Email a password reset link valid for 30 minutes. |
| POST | `/auth/reset-password` | Public | Set a new password using a token from the forgot-password email. |

## Users & team

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/users/me` | Signed in | Current authenticated user's profile. |
| PATCH | `/users/me` | Signed in | Update your display name. |
| POST | `/users/me/password` | Signed in | Change your password after confirming the current one. |
| GET | `/users/me/preferences` | Signed in | Your preferences, with defaults filled in. |
| PUT | `/users/me/preferences` | Signed in | Save preferences. Only the keys you send change. |
| GET | `/users` | admin, manager | Team members in your organization with how many conversations each uploaded. |
| POST | `/users` | admin | Add a member with a temporary password you share with them (no email is sent). |
| PATCH | `/users/{user_id}` | admin | Rename a member, or deactivate/reactivate their account. |
| PATCH | `/users/{user_id}/role` | admin | Update a team member's role (admin only). |

## Conversations

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/conversations` | Signed in | List conversations for the current user's organization. |
| POST | `/conversations/upload` | Signed in | Upload an audio/video file and queue it for AI processing. |
| GET | `/conversations/{conversation_id}` | Signed in | Get conversation details by ID. |
| GET | `/conversations/{conversation_id}/audio` | Signed in | Stream or download the recorded audio file for a conversation. |
| GET | `/conversations/{conversation_id}/transcript` | Signed in | Get transcript segments for a conversation. |
| PATCH | `/conversations/{conversation_id}/speaker-labels` | Signed in | Rename speakers across the transcript, e.g. "Speaker 1" -> "Dana (Customer)". |
| GET | `/conversations/{conversation_id}/insights` | Signed in | Get all AI-generated insights for a conversation. |
| GET | `/conversations/{conversation_id}/processing-status` | Signed in | Poll processing status for a conversation. |
| DELETE | `/conversations/{conversation_id}` | Signed in | Delete a conversation and all associated data. |
| POST | `/conversations/{conversation_id}/reprocess` | Signed in | Clear a conversation's transcript and insights and run the whole pipeline again. |

## Analytics

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/analytics/overview` | Signed in | Key dashboard metrics, with change against the previous window of the same length. |
| GET | `/analytics/conversations` | Signed in | Daily conversation volume (every day in the window, zeros included). |
| GET | `/analytics/sentiment` | Signed in | Sentiment counts and average score per day. |
| GET | `/analytics/objections` | Signed in | Objection categories with frequency, average severity (1-3) and resolution rate. |
| GET | `/analytics/sales` | Signed in | Purchase intent, pipeline stage and deal health distributions plus top competitors. |
| GET | `/analytics/agents` | Signed in | Average AI QA scores overall and per person (agents see only themselves). |
| GET | `/analytics/topics` | Signed in | Most frequent key topics across conversation summaries. |

## AI (Copilot, email, natural-language queries)

| Method | Path | Who | Description |
|---|---|---|---|
| POST | `/ai/copilot/chat` | Signed in | RAG-powered conversational assistant querying conversations, summaries, sales insights, and knowledge base. |
| POST | `/ai/generate-email` | Signed in | Generate a context-aware follow-up email based on conversation insights. |
| POST | `/ai/natural-language-query` | Signed in | Translate natural language questions into safe analytics operations. |

## Action items

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/action-items` | Signed in | List the tasks you can see, newest first. |
| POST | `/action-items` | Signed in | Create a task by hand, optionally linked to a conversation you can see. |
| PATCH | `/action-items/{item_id}` | Signed in | Update a task's description, owner, due date, priority or status. |
| DELETE | `/action-items/{item_id}` | Signed in | Delete a task. |

## Sales pipeline

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/sales/pipeline` | Signed in | Leads with lead score, intent, stage, deal health, last activity and next action. |
| PATCH | `/sales/leads/{conversation_id}` | Signed in | Move a lead to another pipeline stage (overrides the AI's stage). |
| GET | `/sales/objections` | Signed in | Objection frequency and resolution across the conversations you can see. |

## Meetings

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/meetings` | Signed in | Conversations with generated meeting minutes, newest first. |
| GET | `/meetings/{conversation_id}/minutes` | Signed in | Get complete meeting minutes formatted for export. |

## CRM proposals

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/crm/proposals` | Signed in | List AI-proposed CRM field updates for human approval. |
| POST | `/crm/proposals/{proposal_id}/approve` | Signed in | Approve (and optionally edit) a proposed CRM update, then write it through the CRM adapter. |
| POST | `/crm/proposals/{proposal_id}/reject` | Signed in | Reject a proposed CRM update. Nothing is written to the CRM. |

## Knowledge base

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/knowledge-base` | Signed in | List knowledge base documents for current user's organization. |
| POST | `/knowledge-base/upload` | admin | Upload a company knowledge document (PDF/DOCX/TXT/MD) and index it for search. |
| DELETE | `/knowledge-base/{document_id}` | admin | Delete knowledge document and purge its vector embeddings. |

## Reports

| Method | Path | Who | Description |
|---|---|---|---|
| POST | `/reports/generate` | admin, manager | Generate a report from this organization's metrics and save it. |
| GET | `/reports` | admin, manager | Reports saved for this organization, newest first. |
| GET | `/reports/export/csv` | Signed in | Export the conversations you can see, with key AI metrics, as CSV. |
| GET | `/reports/{report_id}` | admin, manager | One saved report. |
| GET | `/reports/{report_id}/download` | admin, manager | Download a saved report as PDF, Markdown or CSV. |

## Integrations

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/integrations` | Signed in | Every integration with its provider, settings and status for this organization. |
| PUT | `/integrations/{key}` | admin | Turn an integration on or off, pick its provider or edit its settings (admin only). |
| POST | `/integrations/talkwisely/sync` | admin, manager | Import new calls from the TalkWisely PBX adapter and queue them for analysis. |
| POST | `/integrations/{key}/test` | admin, manager | Run the configured adapter's health check and report how long it took. |

## Notifications

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/notifications` | Signed in | List in-app notifications for the authenticated user. |
| POST | `/notifications/read-all` | Signed in | Mark every notification for the current user as read. |
| POST | `/notifications/{notification_id}/read` | Signed in | Mark notification as read. |

## System & administration

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/system/ai-settings` | admin, manager | Active providers and models. Secrets are never included. |
| GET | `/system/audit-logs` | admin | Most recent audit events (logins, uploads, deletions, approvals, setting changes). |

## Health

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/health` (no `/api/v1` prefix) | Public | Service status and which AI providers are active |
