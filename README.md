# TalkWiseAI — AI-Powered Meeting, Call & Sales Intelligence Platform

> **Production-quality, academic-grade AI conversation intelligence platform.**
> Transform every business conversation into actionable insights using multi-agent LangGraph AI pipelines.

---

## 🏗️ Architecture

```
TalkWiseAI/
├── backend/          # FastAPI + LangGraph + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/      # REST API routes (auth, conversations, analytics)
│   │   ├── ai/          # 15+ LangGraph pipeline agents
│   │   ├── core/        # Config, security, logging, dependencies
│   │   ├── db/          # Models, session, repositories
│   │   └── workers/     # Celery background tasks
│   └── scripts/         # DB seed, migration scripts
└── frontend/         # Next.js 16 + TypeScript + Tailwind
    └── src/
        ├── app/         # Next.js App Router pages
        ├── components/  # Shared components
        └── lib/         # API client, stores, utilities
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (with virtualenv)
- **Node.js 18+** (npm)
- **PostgreSQL 15+** running locally
- **Redis** running locally

### 1. Database Setup

```sql
-- In psql:
CREATE USER talkwise WITH PASSWORD 'talkwise';
CREATE DATABASE talkwiseai OWNER talkwise;
GRANT ALL PRIVILEGES ON DATABASE talkwiseai TO talkwise;
```

### 2. Backend Setup

```powershell
cd D:\Talkwisely\backend

# Activate virtual environment
.\venv\Scripts\Activate

# Install dependencies (first time)
pip install fastapi uvicorn sqlalchemy alembic asyncpg psycopg2-binary \
    python-jose passlib pydantic pydantic-settings email-validator \
    openai tenacity structlog celery redis aiofiles httpx \
    python-slugify rich pypdf python-docx python-multipart

# Copy env file
Copy-Item .env.example .env

# Start backend (creates tables + seeds demo data automatically)
python start.py
```

**Backend API:** http://localhost:8000
**API Docs:** http://localhost:8000/api/docs

### 3. Frontend Setup

```powershell
cd D:\Talkwisely\frontend

# Install dependencies
npm install --legacy-peer-deps

# Start dev server
npm run dev
```

**Frontend:** http://localhost:3000

---

## 🔐 Demo Credentials

| Role    | Email                            | Password    |
|---------|----------------------------------|-------------|
| Admin   | admin@demo.talkwiseai.com        | admin123    |
| Manager | manager@demo.talkwiseai.com      | manager123  |
| Agent   | agent@demo.talkwiseai.com        | agent123    |

---

## 🤖 AI Pipeline

The system runs **15+ specialized AI agents** in parallel using LangGraph:

| Agent | Purpose |
|-------|---------|
| Clean Transcript | Normalize and label speakers |
| Classification | Detect conversation type and purpose |
| Summarization | Executive + detailed summaries |
| Sentiment Analysis | Multi-dimensional sentiment tracking |
| Intent Detection | Customer intent with evidence |
| Pain Point Extraction | Customer problems and needs |
| Sales Intelligence | Lead score, deal health, buying signals |
| Objection Detection | Categorized objections with responses |
| Entity Extraction | Competitors, products, companies |
| Action Item Extraction | Tasks with owners and priorities |
| Meeting Minutes | Professional formatted minutes |
| Recommendations | Next-step recommendations |
| CRM Update Proposals | Human-approved CRM changes |
| Agent Score | AI quality assessment |

---

## 🔧 Environment Variables

Key variables in `.env`:

```bash
# AI Provider (mock = no API key needed)
LLM_PROVIDER=mock          # Set to 'openai' when ready
LLM_API_KEY=               # Add your OpenAI key here
STT_PROVIDER=mock          # Set to 'whisper_local' for real transcription

# Database
DATABASE_URL=postgresql+asyncpg://talkwise:talkwise@localhost:5432/talkwiseai

# CRM/Integrations (all start as 'mock')
CRM_PROVIDER=mock
```

---

## 📊 Features

- ✅ **JWT Authentication** with RBAC (Admin/Manager/Agent)
- ✅ **File Upload** (MP3, WAV, MP4, MOV) with async processing
- ✅ **Local Whisper STT** (no API key required)
- ✅ **Mock LLM Provider** (full functionality without API key)
- ✅ **OpenAI Provider** (drop-in replacement when key is added)
- ✅ **15+ AI Agents** running in parallel via LangGraph
- ✅ **PostgreSQL** with 30+ relational tables
- ✅ **Celery** background task queue
- ✅ **Analytics Dashboard** with real-time metrics
- ✅ **Demo Data** seeded automatically
- ✅ **Audit Logging** for compliance
- ✅ **Multi-tenant** architecture with organization isolation

---

## 🧪 Running Tests

```powershell
cd D:\Talkwisely\backend
.\venv\Scripts\Activate
pytest tests/ -v --cov=app
```

---

## 📝 API Documentation

Interactive Swagger UI: http://localhost:8000/api/docs
ReDoc: http://localhost:8000/api/redoc

---

*Built with FastAPI, LangGraph, Next.js, PostgreSQL, Celery, and Redis.*
*Academic Project — SGP 10 Credits*
