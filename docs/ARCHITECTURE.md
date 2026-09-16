# TalkWiseAI — System Architecture Documentation

**TalkWiseAI** is a production-grade, academic multi-agent platform for business meeting intelligence, call analytics, and sales enablement designed for the **TalkWisely** business communications ecosystem (Cloud PBX, Hosted PBX, VoIP, Virtual Phone Numbers, Contact Center).

---

## 1. High-Level Architecture Diagram

```
                             ┌───────────────────────────────────┐
                             │       User Ingestion Interfaces   │
                             │ (Web UI, Audio/Video Upload, PBX) │
                             └─────────────────┬─────────────────┘
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │       FastAPI API Gateway         │
                             │ (v1 Routers: /conversations, /ai, │
                             │  /sales, /crm, /knowledge-base)   │
                             └─────────────────┬─────────────────┘
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │    Celery Asynchronous Workers    │
                             │ (Audio Normalization & Ingestion) │
                             └─────────────────┬─────────────────┘
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │   Speech-to-Text & Diarization    │
                             │  (Whisper Provider / Speaker Map) │
                             └─────────────────┬─────────────────┘
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │  LangGraph Multi-Agent Pipeline   │
                             │     (16 Parallel & Sequential     │
                             │        Specialized AI Nodes)      │
                             └─────────────────┬─────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
       ┌───────────────────────────────┐               ┌───────────────────────────────┐
       │   Relational DB (PostgreSQL)  │               │   Vector DB (ChromaDB / RAG)  │
       │ (Transcripts, Insights, Tasks,│               │ (Transcript Chunks & KB Doc   │
       │  Sales Scores, CRM Proposals) │               │          Embeddings)          │
       └───────────────┬───────────────┘               └───────────────┬───────────────┘
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                                               ▼
                             ┌───────────────────────────────────┐
                             │      Integrations Adapter Layer   │
                             │ (TalkWisely PBX, Salesforce CRM,  │
                             │  Google Calendar, Email Dispatch) │
                             └───────────────────────────────────┘
```

---

## 2. Core Subsystems

### A. FastAPI Ingestion & API Layer
- Clean RESTful architecture organized under `/api/v1`.
- Built-in JWT/Session authorization and organization scoping (`organization_id`).
- Asynchronous non-blocking file processing queue backed by Celery and Redis.

### B. Multi-Agent Pipeline (LangGraph)
- Stateful graph pipeline processing conversations through 16 specialized agents.
- Structured JSON outputs strictly validated via Pydantic.
- Pure agent node execution guarantees safety: database operations are batched after graph completion.

### C. Retrieval-Augmented Generation (RAG) & Vector Database
- ChromaDB vector store with in-memory fallback for local execution.
- Metadata filtering enforces strict multi-tenant isolation by `organization_id`.
- Indexes both timestamped transcript segments and uploaded company knowledge documents.

### D. Human-in-the-Loop CRM & Email Guard
- CRM field update proposals (Agent 13) require explicit user approval before execution via `/api/v1/crm`.
- Email drafts require user review prior to dispatching external communications.

---

## 3. Database Schema Overview

Primary relational models in PostgreSQL:
- `organizations`, `users`, `roles`
- `conversations`, `speakers`, `transcript_segments`
- `summaries`, `sentiment_results`, `intent_results`, `sales_insights`
- `action_items`, `objections`, `entities`, `pain_points`
- `meeting_minutes`, `recommendations`, `agent_scores`, `crm_records`
- `knowledge_documents`, `notifications`, `audit_logs`, `processing_jobs`
