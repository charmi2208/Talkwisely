# MASTER PROJECT PROMPT

## TalkWiseAI — AI-Powered Meeting, Call & Sales Intelligence Platform

You are the lead software architect, senior full-stack developer, AI/ML engineer, product designer, and QA engineer responsible for building a complete production-quality academic + industry-grade software project.

Build the entire project end-to-end.

Do NOT build only a UI prototype.

Do NOT create dummy screens without implementing the underlying functionality.

The system must have a functional frontend, backend, database, authentication, AI processing pipeline, multi-agent orchestration, analytics, search, RAG, and modular integrations.

The project will initially be developed using Antigravity. The codebase must therefore be clean, modular, well documented, maintainable, and structured so that it can later be inspected, refactored, enhanced, and extended using Claude Code.

---

# 1. PROJECT IDENTITY

## Project Name

TalkWiseAI

## Full Project Title

AI-Powered Meeting, Call & Sales Intelligence Platform

## Alternative formal academic title

"TalkWiseAI: A Multi-Agent AI Platform for Meeting Intelligence, Conversation Analytics and Sales Enablement"

## Project Type

Full-stack AI-powered SaaS platform.

## Academic Context

This is a 10-credit Semester Group Project (SGP).

Therefore, the project must have sufficient technical depth, software engineering complexity, AI/ML integration, database design, system architecture, testing, documentation, deployment capability, and scalability to justify a major academic project.

---

# 2. BUSINESS CONTEXT

The project is being developed in the domain of TalkWisely, Ahmedabad.

TalkWisely provides:

* AI-powered Cloud PBX
* Business Phone Systems
* Hosted PBX
* VoIP Calling
* Contact Centre Solutions
* Virtual Phone Numbers
* UK/USA/Australia business numbers
* AI Call Analytics
* Conversation Intelligence
* Call Recording
* Quality Monitoring
* Intelligent IVR
* Call Routing
* CRM Integrations
* Sales Solutions
* Customer Support Solutions
* AI/ML-based customer services
* Customer support automation
* Unified communications
* Omnichannel customer support
* Custom AI Agents
* LangChain
* LangGraph
* MCP tools

TalkWiseAI should complement this ecosystem.

The platform should transform raw business conversations into actionable intelligence.

Instead of simply recording calls or meetings, the system should answer:

* What happened?
* What did the customer want?
* What problems were discussed?
* What objections occurred?
* Was the customer interested?
* What decisions were made?
* What action items were created?
* Who owns each action?
* What should happen next?
* Should the CRM be updated?
* What sales opportunity exists?
* How did the agent perform?
* What should the sales representative do next?
* What trends are appearing across conversations?

---

# 3. CORE PROJECT VISION

Build ONE unified platform combining:

## A. AI Sales Intelligence Platform

AND

## B. AI Meeting + Call Intelligence Suite

These are NOT separate applications.

Meeting Intelligence and Call Intelligence are the foundation.

Sales Intelligence is an intelligence layer built on top of those conversations.

The platform should support:

* Sales calls
* Customer calls
* Support calls
* Internal meetings
* Client meetings
* Product demos
* Sales meetings
* Follow-up meetings
* Uploaded audio
* Uploaded video
* Recorded conversations

The same conversation intelligence pipeline should analyze all supported conversation types.

---

# 4. HIGH-LEVEL SYSTEM FLOW

The primary workflow should be:

User uploads or imports:

Audio / Video / Call Recording / Meeting Recording

↓

Media Processing

↓

Speech-to-Text

↓

Speaker Diarization / Speaker Identification

↓

Timestamped Transcript

↓

Conversation Segmentation

↓

Conversation Classification

↓

LangGraph Multi-Agent Processing Pipeline

↓

Specialized AI Agents

↓

Structured Intelligence

↓

Database

↓

Vector Database

↓

Analytics Engine

↓

CRM / Task / Calendar / Email Integrations

↓

Dashboard

↓

AI Search

↓

RAG-based Conversation Assistant

---

# 5. MAIN PRODUCT MODULES

Implement the following major modules.

## Module 1 — Authentication & User Management

Implement:

* Sign up
* Login
* Logout
* Password hashing
* Session/token authentication
* Forgot password architecture
* User profile
* Organization/workspace
* Role-based access control

Roles:

### Admin

Can:

* Manage organization
* Manage users
* View all conversations
* View all analytics
* Configure integrations
* Configure AI settings
* Manage knowledge base

### Manager

Can:

* View team analytics
* View conversations
* View agent scorecards
* View sales intelligence
* Generate reports

### Sales/Support Agent

Can:

* Upload conversations
* View assigned conversations
* View summaries
* View action items
* Use AI assistant
* View personal performance

Design the architecture so additional roles can be added later.

---

# 6. MODULE 2 — CONVERSATION INGESTION

Support multiple ingestion methods.

## A. Upload Audio

Support common formats such as:

* MP3
* WAV
* M4A

## B. Upload Video

Support common video formats where feasible.

Extract audio before transcription.

## C. Call Recording Adapter

Create an abstraction layer for future TalkWisely Cloud PBX integration.

IMPORTANT:

Do not invent undocumented TalkWisely APIs.

Create an interface such as:

CallProviderAdapter

with methods conceptually similar to:

* fetch_calls()
* fetch_call_recording()
* fetch_call_metadata()
* sync_call()

Initially implement a mock/local adapter if real API credentials are unavailable.

The architecture must allow the real TalkWisely API to replace the mock adapter later without rewriting the application.

## D. Meeting Import

Design the system to eventually support:

* Zoom
* Google Meet
* Microsoft Teams

Again, use integration adapters rather than hardcoding third-party APIs.

---

# 7. MODULE 3 — MEDIA PROCESSING

When a file is uploaded:

1. Validate file
2. Validate size
3. Store file securely
4. Create conversation record
5. Create processing job
6. Extract audio if required
7. Normalize audio
8. Send audio to transcription
9. Store transcript
10. Continue AI pipeline

Use background processing for long-running jobs.

Do not block the main API request while processing a long recording.

Create statuses such as:

* uploaded
* queued
* processing
* transcribing
* analyzing
* completed
* failed

Display processing progress in the frontend.

---

# 8. MODULE 4 — SPEECH-TO-TEXT

Use Whisper or another configurable speech-to-text provider.

The transcription layer must be provider-agnostic.

Create an abstraction:

SpeechToTextProvider

Possible implementation:

WhisperProvider

The system should return:

* Transcript
* Timestamp
* Speaker
* Confidence where available
* Language

Example:

00:01:03 — Speaker 1

"Good morning, how can I help you?"

00:01:07 — Speaker 2

"We are looking for an enterprise solution."

Store transcript segments in the database.

---

# 9. MODULE 5 — SPEAKER IDENTIFICATION

Implement speaker segmentation where technically feasible.

Identify:

* Speaker 1
* Speaker 2
* Speaker 3
* etc.

Allow users to rename speakers:

Speaker 1 → Sales Representative

Speaker 2 → Customer

This improves downstream analysis.

Design the data model so speaker identity can later be connected with CRM users or contacts.

---

# 10. MODULE 6 — CONVERSATION INTELLIGENCE ENGINE

This is the central intelligence layer.

Every processed conversation should produce structured insights.

The platform must extract:

* Summary
* Detailed summary
* Key topics
* Important moments
* Decisions
* Action items
* Questions
* Answers
* Customer intent
* Sentiment
* Objections
* Pain points
* Buying signals
* Competitor mentions
* Product mentions
* Pricing discussions
* Budget discussions
* Decision-maker information
* Timeline
* Next steps
* Risks
* Opportunities
* Follow-up requirements

---

# 11. MULTI-AGENT ARCHITECTURE

Use LangGraph as the primary orchestration framework.

Do NOT simply call one giant LLM prompt and claim it is a multi-agent system.

Create specialized agents with clearly separated responsibilities.

The agents should operate within an orchestrated workflow.

---

# 12. AGENT 1 — TRANSCRIPTION / DOCUMENT PROCESSING AGENT

## Responsibility

Prepare raw conversation data for downstream agents.

Tasks:

* Validate transcript
* Clean transcript
* Preserve timestamps
* Preserve speaker information
* Remove obvious transcription artifacts
* Segment conversation
* Identify conversation sections
* Detect language
* Prepare structured conversation representation

Output:

Structured transcript.

---

# 13. AGENT 2 — CONVERSATION CLASSIFICATION AGENT

Determine the type of conversation.

Possible classifications:

* Sales
* Customer Support
* Follow-up
* Product Demo
* Internal Meeting
* Client Meeting
* Complaint
* General Business Conversation
* Other

Also determine:

* Primary purpose
* Participants
* Business context

This classification determines which downstream analysis should receive more importance.

---

# 14. AGENT 3 — SUMMARIZATION AGENT

Generate:

## Executive Summary

Short overview of the entire conversation.

## Detailed Summary

Important points in chronological/business order.

## Key Discussion Points

Major topics discussed.

## Decisions

Decisions made during the conversation.

## Important Moments

Timestamped important conversation segments.

Do not produce vague summaries.

Summaries must be grounded in the transcript.

---

# 15. AGENT 4 — ACTION ITEM AGENT

Extract every actionable task.

For each task identify:

* Task description
* Owner
* Source speaker
* Due date if mentioned
* Priority
* Status
* Related topic
* Timestamp

Example:

Task:

Send Enterprise pricing proposal

Owner:

Sales Representative

Due:

Friday

Priority:

High

If owner or due date is not explicitly known, mark it as unknown instead of hallucinating.

---

# 16. AGENT 5 — SENTIMENT & EMOTION AGENT

Analyze:

* Overall sentiment
* Sentiment throughout the conversation
* Customer sentiment
* Agent sentiment
* Positive moments
* Negative moments
* Frustration
* Satisfaction
* Neutral sections

Possible output:

Overall sentiment:

Positive

Customer sentiment:

Mostly positive

Trend:

Neutral → Interested → Positive

Provide timestamps for important sentiment changes where possible.

Avoid pretending that emotion detection is perfectly accurate.

---

# 17. AGENT 6 — CUSTOMER INTENT AGENT

Determine what the customer actually wants.

Possible intents:

* Product inquiry
* Pricing inquiry
* Demo request
* Purchase intent
* Support request
* Complaint
* Cancellation
* Upgrade
* Integration request
* Feature request
* Information request
* Other

Return:

* Primary intent
* Secondary intents
* Confidence
* Evidence
* Relevant timestamps

---

# 18. AGENT 7 — PAIN POINT & NEEDS AGENT

Extract:

* Customer pain points
* Business problems
* Operational problems
* Technical problems
* Current solution limitations
* Desired outcomes
* Requirements

Map:

Problem → Need → Potential Solution

---

# 19. AGENT 8 — SALES INTELLIGENCE AGENT

This is one of the most important agents.

Analyze sales-related conversations for:

* Buying signals
* Purchase intent
* Lead quality
* Customer needs
* Decision-maker presence
* Budget
* Timeline
* Authority
* Need
* Competition
* Objections
* Product fit
* Upsell opportunity
* Cross-sell opportunity
* Closing probability

Generate:

### Lead Score

0–100

### Purchase Intent

Low / Medium / High

### Deal Health

Healthy / At Risk / Critical

### Recommended Next Action

Examples:

* Schedule demo
* Send proposal
* Follow up
* Offer technical consultation
* Escalate
* Contact decision maker

Every important conclusion should include supporting transcript evidence where possible.

---

# 20. AGENT 9 — OBJECTION DETECTION AGENT

Detect sales objections such as:

* Price
* Features
* Security
* Integration
* Competitor
* Timing
* Contract
* Complexity
* Trust
* Implementation
* Support

For every objection:

* Objection category
* Exact meaning
* Timestamp
* Severity
* Suggested response
* Whether objection was resolved

---

# 21. AGENT 10 — COMPETITOR & ENTITY AGENT

Detect mentions of:

* Competitors
* Products
* Companies
* Technologies
* Features
* Locations
* People
* Pricing
* Plans

Store entities in structured form.

Track competitor frequency across conversations.

---

# 22. AGENT 11 — MEETING MINUTES AGENT

Generate professional meeting minutes.

Format:

### Meeting Objective

### Participants

### Discussion Points

### Decisions

### Action Items

### Open Questions

### Risks

### Next Steps

### Next Meeting

Allow export to PDF and other suitable formats.

---

# 23. AGENT 12 — EMAIL GENERATION AGENT

Generate context-aware follow-up emails.

Types:

* Thank-you email
* Meeting summary
* Proposal follow-up
* Demo follow-up
* Reminder
* Sales follow-up
* Support follow-up

The email must be based strictly on conversation data.

Allow tone:

* Professional
* Friendly
* Concise
* Formal

Allow user editing before sending.

---

# 24. AGENT 13 — CRM UPDATE AGENT

Determine which CRM information should be updated.

Possible updates:

* Lead status
* Opportunity stage
* Contact notes
* Customer requirements
* Call summary
* Next action
* Follow-up date
* Deal health

IMPORTANT:

The agent must NOT silently modify production CRM data.

Show proposed changes first.

Example:

AI proposes:

Lead Stage:

Qualified → Proposal

User can:

Approve

Reject

Edit

Only after approval should an external CRM adapter execute the update.

---

# 25. AGENT 14 — RECOMMENDATION AGENT

Based on all extracted intelligence, recommend what should happen next.

Examples:

* Schedule demo
* Send pricing
* Send documentation
* Contact decision maker
* Follow up after 3 days
* Escalate technical issue
* Offer enterprise plan
* Schedule support call

Recommendations must have reasoning/evidence.

---

# 26. AGENT 15 — AGENT PERFORMANCE / QA AGENT

Evaluate the sales/support representative.

Metrics:

* Greeting
* Professionalism
* Clarity
* Empathy
* Listening
* Question quality
* Response quality
* Product knowledge
* Objection handling
* Sales technique
* Closing technique
* Talk/listen ratio
* Interruptions
* Filler words
* Silence
* Script compliance where a script exists

Generate:

Overall Score: 0–100

Strengths

Weaknesses

Improvement Suggestions

Coaching Recommendations

Do not present subjective AI judgments as objective truth.

Clearly label them as AI-generated assessments.

---

# 27. AGENT 16 — CONVERSATION SEARCH / RAG AGENT

Create a RAG system over processed conversations.

Users should be able to ask questions such as:

"Which customers discussed pricing?"

"Which leads showed high buying intent?"

"Which conversations mentioned API integration?"

"Show calls where customers complained about support."

"Which customers requested a demo?"

"Summarize all conversations related to Enterprise plans."

The system should retrieve relevant transcript chunks and generate answers grounded in those chunks.

Use:

* Embeddings
* Vector database
* Metadata filtering
* Retrieval
* Reranking where appropriate
* LLM generation

Always provide source conversation references and timestamps where possible.

---

# 28. AGENT 17 — EXECUTIVE REPORT AGENT

Generate management reports.

Examples:

### Daily Report

### Weekly Report

### Monthly Report

### Sales Performance Report

### Conversation Quality Report

### Customer Sentiment Report

### Objection Analysis

### Competitor Analysis

### Team Performance Report

Include:

* Key statistics
* Trends
* Important changes
* Risks
* Opportunities
* Recommended actions

---

# 29. LANGGRAPH ORCHESTRATION

Design the pipeline as a stateful graph.

Conceptually:

START

↓

Input Validation

↓

Transcription

↓

Speaker Processing

↓

Conversation Classification

↓

Parallel Analysis

├── Summary Agent

├── Sentiment Agent

├── Intent Agent

├── Pain Point Agent

├── Sales Intelligence Agent

├── Objection Agent

├── Competitor Agent

└── Action Item Agent

↓

Aggregate Intelligence

↓

Meeting Intelligence

↓

CRM Intelligence

↓

Recommendation Agent

↓

QA Agent

↓

Store Results

↓

Generate Embeddings

↓

Index in Vector DB

↓

END

Agents should execute independently where possible.

Use structured outputs / schemas.

Do not rely on fragile free-form LLM responses.

---

# 30. DATABASE

Use PostgreSQL as the primary relational database.

Design normalized schemas for at least:

users

organizations

roles

conversations

participants

speakers

transcripts

transcript_segments

conversation_topics

summaries

action_items

sentiments

intents

pain_points

buying_signals

objections

competitors

entities

sales_insights

recommendations

agent_scores

meetings

crm_records

integrations

notifications

reports

knowledge_documents

audit_logs

processing_jobs

AI_outputs

Create appropriate:

* Primary keys
* Foreign keys
* Indexes
* Timestamps
* Status fields
* Organization scoping

Every organization's data must be logically isolated.

---

# 31. VECTOR DATABASE

Use ChromaDB, FAISS, or another suitable vector database.

Store embeddings for:

* Transcript chunks
* Meeting summaries
* Key discussion points
* Knowledge documents

Metadata should include:

* organization_id
* conversation_id
* speaker
* timestamp
* conversation_type
* date
* topic
* customer/contact if available

This allows filtered RAG.

---

# 32. KNOWLEDGE BASE

Create a knowledge base module.

Users can upload:

* PDFs
* DOCX
* TXT
* FAQs
* Product documents
* Sales documentation
* Support documentation
* Internal policies

Pipeline:

Upload

↓

Extract text

↓

Chunk

↓

Embed

↓

Store

↓

Retrieve

↓

RAG Assistant

The AI should be able to use company knowledge alongside conversation information.

---

# 33. AI COPILOT

Create a global AI assistant.

Users can ask:

"What happened in today's sales calls?"

"Which leads need follow-up?"

"What are the biggest customer complaints?"

"Summarize my meetings."

"Which objections are increasing?"

"Which sales agents need coaching?"

"Show customers with high buying intent."

The assistant should use tools rather than relying only on an LLM.

Potential tools:

* search_conversations
* get_conversation
* get_sales_insights
* get_customer
* get_action_items
* search_knowledge_base
* get_team_analytics
* generate_report

Use controlled tool calling.

---

# 34. NATURAL LANGUAGE ANALYTICS

Users should be able to ask analytical questions.

Examples:

"How many high-intent leads did we have this month?"

"Which objection appeared most frequently?"

"What percentage of calls were positive?"

"Which sales representative had the highest average score?"

"Which customers mentioned competitors?"

Translate questions into safe analytical operations.

Never allow an LLM to directly execute arbitrary SQL.

Use validated query tools or predefined analytics functions.

---

# 35. DASHBOARD

Build a modern SaaS-style dashboard.

Main dashboard should show:

* Total conversations
* Calls
* Meetings
* Processing status
* High-intent leads
* Open action items
* Follow-ups
* Average sentiment
* Sales opportunities
* Conversion indicators
* Agent performance

Include charts for:

* Conversation volume
* Sentiment trends
* Sales intent
* Objection trends
* Agent performance
* Call duration
* Topic trends

Allow:

* Date filtering
* Team filtering
* Agent filtering
* Conversation type filtering

---

# 36. CONVERSATION DETAILS PAGE

For every conversation provide:

## Header

* Conversation title
* Date
* Duration
* Type
* Participants
* Status

## Tabs

### Overview

Summary and key insights.

### Transcript

Timestamped speaker transcript.

### Sales Intelligence

* Lead score
* Purchase intent
* Buying signals
* Objections
* Competitors
* Deal health

### Meeting Intelligence

* Decisions
* Action items
* Next steps
* Minutes

### Sentiment

Sentiment timeline.

### Agent Score

Performance evaluation.

### AI Chat

Ask questions about this conversation.

### Recommended Actions

AI suggestions.

---

# 37. TRANSCRIPT UI

Create a professional transcript viewer.

Features:

* Speaker labels
* Timestamps
* Search
* Highlight
* Jump to timestamp
* Sentiment indicators
* Important moment markers

When the user clicks an insight, navigate to the corresponding transcript timestamp.

Example:

"Pricing objection detected at 12:42"

Click → transcript jumps to 12:42.

---

# 38. SALES PIPELINE

Create an optional sales intelligence view.

Stages:

* New
* Contacted
* Qualified
* Demo
* Proposal
* Negotiation
* Won
* Lost

Show:

* Lead score
* Purchase intent
* Last conversation
* Next action
* Deal health

This should be powered by conversation intelligence rather than manually entered information alone.

---

# 39. ACTION ITEM MANAGEMENT

Create a task system.

Every action item should support:

* Task
* Owner
* Due date
* Priority
* Source conversation
* Status
* Created date

Statuses:

* Pending
* In Progress
* Completed
* Overdue

Allow users to edit and mark complete.

---

# 40. NOTIFICATION SYSTEM

Create notification architecture.

Notify users about:

* Processing completion
* Failed processing
* Upcoming follow-up
* Overdue task
* High-intent lead
* Important customer issue
* AI-generated recommendation

Initially implement in-app notifications.

Design adapters for email notifications later.

---

# 41. CRM INTEGRATION ARCHITECTURE

Do not hardcode a specific CRM.

Create:

CRMProvider interface.

Potential providers:

* Salesforce
* HubSpot
* Zoho

Initially implement:

MockCRMProvider

The UI should allow:

Integration

↓

Authenticate

↓

Test connection

↓

Sync

The architecture must allow future real integrations.

---

# 42. CALENDAR INTEGRATION ARCHITECTURE

Create:

CalendarProvider interface.

Potential:

* Google Calendar
* Microsoft Outlook Calendar

Initially use mock/local implementation if credentials are unavailable.

AI recommendations can propose meeting times.

---

# 43. EMAIL INTEGRATION ARCHITECTURE

Create:

EmailProvider interface.

Initially generate drafts.

Sending should require explicit user confirmation.

Do not automatically send external emails without user approval.

---

# 44. TALKWISELY INTEGRATION ARCHITECTURE

This is especially important because the project is intended to be related to TalkWisely.

Create an integration layer that can eventually connect:

TalkWisely Cloud PBX

↓

Call Metadata

↓

Call Recording

↓

TalkWiseAI

↓

AI Analysis

↓

Insights

↓

TalkWisely Dashboard / CRM

Do not invent APIs or pretend a real integration exists if API documentation/credentials are unavailable.

Use mock adapters and realistic sample data during development.

Keep the integration boundary clean.

---

# 45. API DESIGN

Use FastAPI.

Organize endpoints by domain.

Examples:

/auth

/users

/organizations

/conversations

/transcripts

/insights

/sales

/meetings

/action-items

/reports

/analytics

/search

/knowledge-base

/integrations

/crm

/calendar

/notifications

/ai

Use:

* Pydantic schemas
* Request validation
* Response schemas
* Error handling
* Authentication
* Authorization
* Logging
* API documentation

Generate OpenAPI documentation automatically.

---

# 46. FRONTEND

Use:

React.js or Next.js.

Preferred:

Next.js + TypeScript.

Use a modern component architecture.

Important pages:

/login

/register

/dashboard

/conversations

/conversations/[id]

/meetings

/sales

/leads

/action-items

/analytics

/reports

/knowledge-base

/ai-assistant

/team

/settings

/integrations

/profile

---

# 47. UI/UX DESIGN

The interface must look like a professional B2B SaaS product.

Design principles:

* Clean
* Modern
* Minimal
* Professional
* Data-focused
* Responsive
* Accessible

Avoid:

* Excessive animations
* Random gradients everywhere
* Fake glassmorphism
* Unnecessary decorative components
* Dashboard clutter

Prioritize information hierarchy.

---

# 48. RESPONSIVE DESIGN

Support:

* Desktop
* Laptop
* Tablet

Mobile should have a usable responsive experience for important pages.

---

# 49. SEARCH

Implement global search.

Search:

* Conversations
* Meetings
* Customers
* Topics
* Competitors
* Action items

Include semantic search using vector embeddings.

---

# 50. FILTERING

Conversation filtering:

* Date
* Duration
* Type
* Agent
* Customer
* Sentiment
* Intent
* Lead score
* Processing status

---

# 51. SECURITY

Implement proper security.

Requirements:

* Password hashing
* JWT/session authentication
* RBAC
* Input validation
* File validation
* Secure file handling
* API authorization
* Organization-level isolation
* Audit logs
* Rate limiting architecture
* Secret management
* Environment variables
* No API keys committed to Git
* CORS configuration
* Error sanitization

Do not expose sensitive transcript data unnecessarily.

---

# 52. PRIVACY

Conversation recordings and transcripts can contain sensitive business information.

Design accordingly.

Implement:

* Access control
* Organization isolation
* Audit logs
* Data deletion architecture
* Secure storage abstraction

Clearly identify AI-generated outputs.

---

# 53. AI RELIABILITY

Do not blindly trust LLM output.

Use:

* Structured JSON schemas
* Validation
* Confidence scores where appropriate
* Evidence extraction
* Transcript citations
* Retry handling
* Fallback behavior
* Hallucination prevention

If information is not present in the conversation, the AI should say:

"Not found in the available conversation."

Never invent:

* Customer commitments
* Dates
* Prices
* People
* Decisions
* CRM fields

---

# 54. AI PROVIDER ABSTRACTION

Do not tightly couple the system to one LLM provider.

Create:

LLMProvider interface.

Allow future implementations such as:

* OpenAI
* Anthropic
* Gemini
* Local models
* Other OpenAI-compatible APIs

The application should use environment configuration to select the provider.

---

# 55. EMBEDDING PROVIDER ABSTRACTION

Create:

EmbeddingProvider interface.

Allow future replacement of embedding models.

---

# 56. SPEECH PROVIDER ABSTRACTION

Create:

SpeechToTextProvider interface.

This allows Whisper to later be replaced by another provider.

---

# 57. BACKGROUND JOB ARCHITECTURE

Long-running tasks must be asynchronous.

Examples:

* Transcription
* Embedding
* AI analysis
* Report generation
* File processing

Use a job/queue architecture.

A lightweight initial implementation may use:

* Celery + Redis

or another appropriate task queue.

Keep the architecture modular.

---

# 58. CACHING

Use Redis where useful for:

* Job status
* Temporary processing state
* Rate limiting
* Frequently accessed analytics
* AI response caching where safe

---

# 59. LOGGING

Implement structured logging.

Log:

* Authentication events
* API errors
* Processing jobs
* AI failures
* Integration failures
* Important user actions

Never log:

* Passwords
* API keys
* Sensitive secrets

---

# 60. ERROR HANDLING

Every layer must have meaningful error handling.

Frontend:

User-friendly errors.

Backend:

Structured errors.

AI:

Retry + fallback.

File processing:

Failed status + reason.

Integration:

Connection error + recovery guidance.

Do not silently swallow exceptions.

---

# 61. TESTING

This is a 10-credit academic project.

Testing is mandatory.

Implement:

## Unit Tests

For:

* AI parsers
* Validators
* Business logic
* Database services
* Analytics functions

## Integration Tests

For:

* Authentication
* Conversation processing
* AI pipeline
* RAG
* CRM adapters
* API endpoints

## End-to-End Tests

Test workflows such as:

User login

↓

Upload recording

↓

Transcription

↓

AI analysis

↓

View insights

↓

Create follow-up

↓

Generate email

↓

Approve CRM update

---

# 62. AI EVALUATION

Create a small evaluation dataset.

Include manually verified examples.

Evaluate:

* Summary quality
* Action item extraction
* Intent classification
* Sentiment classification
* Objection detection
* Sales intent
* Entity extraction

Use appropriate metrics where possible.

Examples:

* Precision
* Recall
* F1
* Accuracy
* Structured output validity

For generative tasks, use human evaluation criteria.

Do not claim unrealistic accuracy.

---

# 63. SAMPLE DATA

Provide realistic synthetic sample data.

Create sample:

* Sales calls
* Support calls
* Internal meetings
* Client meetings
* Product demos

Do not use real confidential company data unless explicitly authorized.

The demo dataset should make the application fully demonstrable without requiring live TalkWisely APIs.

---

# 64. DEMO MODE

Create a demo mode.

A user should be able to open the application and immediately see:

* Conversations
* Sales insights
* Meeting summaries
* Analytics
* Action items
* AI assistant

Also allow processing a new sample recording.

---

# 65. REPORT GENERATION

Allow users to generate reports.

Formats where practical:

* PDF
* CSV

Reports:

* Conversation report
* Sales report
* Agent performance
* Customer sentiment
* Objection report
* Executive report

---

# 66. AUDIT LOG

Track important actions:

* Login
* Upload
* Delete
* CRM approval
* Integration changes
* AI processing
* Report generation
* User changes

---

# 67. DATABASE SEEDING

Create a seed system.

Running the seed process should create:

* Demo organization
* Demo users
* Demo conversations
* Demo customers
* Demo insights
* Demo action items
* Demo analytics

This makes the application immediately demonstrable.

---

# 68. PROJECT STRUCTURE

Use a clean monorepo or clearly separated frontend/backend structure.

Example:

/frontend

/backend

/ai

/database

/docs

/tests

/scripts

/docker

/config

Create clear README files where useful.

Separate:

* API layer
* Business logic
* Database layer
* AI agents
* AI providers
* Integrations
* Utilities
* Schemas

Do not create a giant monolithic file.

---

# 69. DOCUMENTATION

Create comprehensive documentation.

Include:

README

Architecture documentation

API documentation

Database schema

AI architecture

Agent documentation

Setup guide

Environment variables

Deployment guide

Testing guide

Integration guide

Developer guide

User guide

---

# 70. SYSTEM ARCHITECTURE DOCUMENTATION

Document:

Frontend

↓

API Gateway / FastAPI

↓

Authentication

↓

Business Services

↓

AI Orchestration

↓

LangGraph

↓

Specialized Agents

↓

LLM / STT / Embeddings

↓

PostgreSQL + Vector DB

↓

External Integrations

Provide architecture diagrams in the documentation.

---

# 71. ENVIRONMENT CONFIGURATION

Use `.env.example`.

Include placeholders for:

DATABASE_URL

JWT_SECRET

LLM_API_KEY

LLM_PROVIDER

EMBEDDING_PROVIDER

SPEECH_PROVIDER

REDIS_URL

VECTOR_DB_PATH

STORAGE configuration

CRM configuration

Calendar configuration

Email configuration

Never commit real credentials.

---

# 72. DOCKER

Create Docker configuration for:

Frontend

Backend

PostgreSQL

Redis

Vector database if required

The complete system should be runnable locally using Docker Compose where practical.

---

# 73. DEPLOYMENT

Design for deployment.

Potential architecture:

Frontend → Vercel or equivalent

Backend → Cloud service

PostgreSQL → Managed PostgreSQL

Redis → Managed Redis

Storage → Object storage

Do not hardcode a specific cloud provider unless required.

Provide deployment documentation.

---

# 74. PERFORMANCE

Optimize:

* Large transcript processing
* Database queries
* Vector retrieval
* Dashboard analytics
* API response times

Use pagination.

Do not load thousands of transcript segments into the browser at once.

---

# 75. SCALABILITY

The architecture should eventually support:

Hundreds of users

Thousands of conversations

Large transcript volumes

Multiple organizations

Multiple AI providers

Multiple CRM integrations

Do not optimize prematurely, but keep clear scalability boundaries.

---

# 76. MULTI-TENANCY

The system should be organization-aware.

Every major entity should be associated with:

organization_id

Users should only access resources belonging to their organization unless they have explicitly authorized cross-organization administrative access.

---

# 77. USER WORKFLOW

The primary user journey should be:

1. Login
2. Open Dashboard
3. Upload or import a conversation
4. Processing begins
5. Transcription completes
6. AI analysis runs
7. User receives notification
8. Open conversation
9. View transcript
10. View summary
11. View sales intelligence
12. View sentiment
13. View objections
14. View action items
15. Review AI recommendations
16. Generate follow-up email
17. Approve CRM changes
18. Create follow-up task
19. Search conversation through AI assistant
20. View analytics

This workflow must work end-to-end.

---

# 78. IMPORTANT PRODUCT PRINCIPLE

Do NOT build 20 disconnected AI features.

Everything must revolve around the central entity:

CONVERSATION.

A conversation produces:

Transcript

↓

Insights

↓

Sales Intelligence

↓

Meeting Intelligence

↓

Tasks

↓

Recommendations

↓

CRM updates

↓

Analytics

↓

Knowledge

↓

Search

↓

Reports

This should be reflected in the database, APIs, UI, and architecture.

---

# 79. WHAT MAKES THIS DIFFERENT FROM A BASIC CALL SUMMARIZER

The system must NOT stop at:

"Here is your summary."

It should transform:

Raw conversation

into

Structured business intelligence.

The final value proposition is:

### Record → Understand → Analyze → Recommend → Act → Measure

---

# 80. FINAL DASHBOARD EXPERIENCE

The final application should allow a manager to understand the state of their business conversations at a glance.

Example dashboard:

---

CONVERSATIONS

1,248

---

HIGH INTENT LEADS

84

---

OPEN FOLLOW-UPS

37

---

AVG SENTIMENT

Positive

---

AVG AGENT SCORE

87/100

---

TOP OBJECTION

Pricing

---

SALES OPPORTUNITIES

₹ / $ configurable

---

Then show:

Conversation Trends

Sales Intent Trends

Sentiment Trends

Objection Trends

Agent Performance

Customer Topics

---

# 81. AI ASSISTANT EXAMPLES

The assistant should answer questions like:

"Summarize my sales activity this week."

"Which customers are most likely to buy?"

"Which leads need immediate follow-up?"

"What are the top three objections this month?"

"Which competitor is mentioned most frequently?"

"Which agents need coaching?"

"Show all high-intent conversations."

"Find conversations where customers complained about pricing."

"Which customers requested an integration?"

"Create a follow-up email for this customer."

"Summarize today's meetings."

---

# 82. IMPORTANT SAFETY / TRUST RULES

The AI must distinguish between:

FACT

INFERENCE

RECOMMENDATION

Example:

Fact:

"Customer asked about enterprise pricing."

Inference:

"Customer may have purchase interest."

Recommendation:

"Follow up with enterprise pricing."

Do not present inference or recommendation as confirmed fact.

---

# 83. DEVELOPMENT STRATEGY

Do NOT attempt to implement every feature simultaneously.

Build in vertical slices.

## Phase 1

Project foundation

* Repository
* Frontend
* Backend
* Database
* Authentication
* Docker
* Environment configuration

## Phase 2

Conversation management

* Upload
* Storage
* Processing jobs
* Conversation database
* Transcript UI

## Phase 3

Speech + AI

* STT
* Transcript
* LangGraph
* Summary
* Action items
* Sentiment
* Intent

## Phase 4

Sales Intelligence

* Buying signals
* Lead scoring
* Objections
* Competitors
* Deal health
* Recommendations

## Phase 5

Meeting Intelligence

* Meeting minutes
* Decisions
* Follow-ups
* Email generation

## Phase 6

RAG

* Embeddings
* Vector DB
* Conversation search
* Knowledge base
* AI assistant

## Phase 7

Analytics

* Dashboard
* Sales analytics
* Team analytics
* Sentiment analytics
* Objection analytics

## Phase 8

Integrations

* Mock CRM
* Mock Calendar
* Email adapter
* TalkWisely adapter

## Phase 9

Testing + Security

* Unit tests
* Integration tests
* E2E
* Security
* Validation
* Error handling

## Phase 10

Production polish

* UX
* Performance
* Documentation
* Deployment
* Demo mode
* Final cleanup

---

# 84. DEVELOPMENT RULES

Follow these rules throughout development:

1. Never fake functionality when it can reasonably be implemented.

2. Never create buttons that do nothing.

3. Every major UI action must connect to a real backend operation.

4. Use mock adapters only where external credentials/API access is unavailable.

5. Clearly mark mocked integrations.

6. Never hardcode secrets.

7. Never invent TalkWisely APIs.

8. Use typed interfaces.

9. Use structured AI outputs.

10. Validate all AI-generated structured data.

11. Keep agents modular.

12. Keep providers replaceable.

13. Keep database access separate from business logic.

14. Keep frontend and backend responsibilities separated.

15. Use meaningful naming.

16. Add comments only where they explain non-obvious logic.

17. Avoid unnecessary dependencies.

18. Handle failures gracefully.

19. Never silently discard errors.

20. Do not claim an AI prediction is guaranteed.

---

# 85. ANTIGRAVITY EXECUTION INSTRUCTIONS

You are responsible for actually implementing this system.

Before coding:

1. Analyze the complete requirements.
2. Create the system architecture.
3. Identify dependencies.
4. Create the database schema.
5. Create the repository structure.
6. Define API contracts.
7. Define AI agent contracts.
8. Define integration interfaces.
9. Create an implementation roadmap.

Then implement the project incrementally.

After each major phase:

* Run the application.
* Run tests.
* Fix errors.
* Verify frontend/backend communication.
* Verify database operations.
* Verify AI outputs.
* Verify UI flows.

Do not merely generate source files without validating them.

---

# 86. FINAL ACCEPTANCE CRITERIA

The project will be considered complete only when a user can:

1. Register/login.
2. Access a dashboard.
3. Upload an audio recording.
4. See processing status.
5. Receive a transcript.
6. See speakers.
7. Receive an AI summary.
8. See key topics.
9. See sentiment.
10. See customer intent.
11. See pain points.
12. See action items.
13. See buying signals.
14. See objections.
15. See competitors.
16. Receive a lead score.
17. Receive deal-health analysis.
18. Receive recommended next actions.
19. Receive an agent performance score.
20. Generate meeting minutes.
21. Generate a follow-up email.
22. Review proposed CRM changes.
23. Approve/reject CRM changes.
24. Search conversations.
25. Ask questions about a conversation.
26. Ask questions across conversations using RAG.
27. Upload knowledge documents.
28. Ask questions against the knowledge base.
29. View sales analytics.
30. View team analytics.
31. View sentiment analytics.
32. View objection analytics.
33. Create/manage action items.
34. Generate reports.
35. View notifications.
36. Manage users and roles.
37. Configure integration adapters.
38. Run the entire application locally.
39. Run automated tests.
40. Understand the system through complete documentation.

---

# 87. ACADEMIC SGP REQUIREMENTS

Because this is a 10-credit SGP, the implementation should also produce material for:

## Problem Statement

Automating analysis of business conversations and converting unstructured conversational data into actionable sales, customer-service, and meeting intelligence.

## Objectives

* Automate transcription.
* Automate conversation understanding.
* Extract actionable intelligence.
* Improve sales productivity.
* Improve meeting productivity.
* Improve agent performance.
* Automate follow-ups.
* Support CRM workflows.
* Provide organization-wide conversation analytics.
* Build a scalable multi-agent AI architecture.

## Expected Outcomes

A functional AI-powered platform capable of processing business conversations and producing actionable intelligence for sales, support, managers, and executives.

---

# 88. FUTURE SCOPE

Design the architecture so future versions can add:

* Real-time call intelligence
* Live agent assistance
* Real-time next-best-action recommendations
* Real-time objection detection
* Voice AI
* Automatic call routing
* Advanced forecasting
* Predictive churn
* Revenue forecasting
* More CRM integrations
* More communication channels
* WhatsApp intelligence
* Email intelligence
* Social conversation intelligence
* Enterprise SSO
* Advanced compliance
* Custom organization-specific AI agents
* MCP-based enterprise tools

These are future scope items unless they are necessary for the core MVP.

Do not allow future-scope features to destabilize the core system.

---

# 89. FINAL PRODUCT DEFINITION

The final product is:

## TalkWiseAI

An AI-powered business conversation intelligence platform that converts meetings and calls into structured sales intelligence, meeting intelligence, customer intelligence, actionable tasks, recommendations, CRM updates, performance insights, and organization-wide analytics.

The platform combines:

### Conversation Intelligence

*

### Meeting Intelligence

*

### Sales Intelligence

*

### AI Agent Assistance

*

### RAG

*

### Analytics

*

### CRM Workflow

*

### Follow-up Automation

into ONE unified system.

The core philosophy is:

# "Every conversation should become actionable business intelligence."

Build the system around this principle.

---

# 90. FINAL INSTRUCTION

Start by analyzing the requirements and generating the technical implementation plan.

Then begin implementation.

Do not ask me to manually create dozens of files.

Create the required project structure and implement the application.

When an external service requires credentials that are not available:

* Build the provider interface.
* Build a mock provider.
* Build realistic demo data.
* Keep the real integration boundary ready.

When an AI provider requires an API key:

* Read it from environment variables.
* Never hardcode it.
* Provide `.env.example`.

When uncertain about an external API:

* Do not invent endpoints.
* Create an adapter abstraction.

Prioritize:

1. Correctness
2. End-to-end functionality
3. Clean architecture
4. AI reliability
5. Security
6. Maintainability
7. UX
8. Performance
9. Documentation
10. Visual polish

Do not optimize for screenshots alone.

Build a real working application.

The first milestone should be a functional vertical slice:

Login

→ Upload conversation

→ Transcribe

→ Analyze with LangGraph

→ Generate structured intelligence

→ Store in PostgreSQL

→ Display results in the frontend

Once this works reliably, expand the system module by module until the complete TalkWiseAI platform is implemented.