# TalkWiseAI

**AI-Powered Meeting, Call & Sales Intelligence Platform**

TalkWiseAI turns recorded sales calls, support calls and meetings into structured business intelligence: transcripts with speaker roles, summaries, sentiment, customer intent, lead scores, objections, action items, CRM update proposals and agent quality scores. Everything is searchable, and an AI Copilot answers questions with cited sources.

Built for the TalkWisely (Ahmedabad) Cloud PBX ecosystem as a 10-credit Semester Group Project (SGP).

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui, light and dark mode |
| Backend | FastAPI, SQLAlchemy (async), Pydantic, JWT authentication with role-based access |
| AI pipeline | Multi-agent conversation pipeline (LangGraph-style state graph, run with asyncio) |
| LLM | Any OpenAI-compatible API. Default: Groq `openai/gpt-oss-120b` (free tier) |
| Speech-to-text | Hosted Whisper (`whisper-large-v3-turbo` on Groq), with ffmpeg audio preprocessing |
| Semantic search | ChromaDB with local ONNX embeddings (all-MiniLM-L6-v2, no API key needed) |
| Database | SQLite for local development; PostgreSQL supported |
| Integrations | Adapter interfaces for TalkWisely PBX, CRM, calendar and email (mock implementations for now) |

---

## Project structure

```
Talkwisely/
├── backend/                 FastAPI app
│   ├── app/
│   │   ├── api/v1/          REST routes (auth, conversations, ai, crm, reports, ...)
│   │   ├── ai/
│   │   │   ├── pipeline/    Conversation pipeline: state, nodes (agents), graph
│   │   │   ├── agents/      Copilot (RAG), follow-up email, executive report agents
│   │   │   ├── providers/   LLM, speech-to-text and embedding providers (real + mock)
│   │   │   └── rag/         Vector store and conversation indexer
│   │   ├── core/            Settings, security, logging, dependencies
│   │   ├── db/              Models, session, AI-output sanitizer
│   │   ├── integrations/    PBX / CRM / calendar / email adapters
│   │   └── workers/         Background processing of uploaded recordings
│   ├── scripts/             seed.py (demo data), reindex.py (search index)
│   ├── tests/               Smoke suite, unit and integration tests
│   ├── start.py             Creates tables, seeds, indexes, starts the server
│   └── .env.local.example   Template for local settings and API keys
├── frontend/                Next.js app
│   └── src/
│       ├── app/             Pages: (auth) login/register, (dashboard) app pages
│       ├── components/      ui/ (shadcn), layout/, conversation/, auth/
│       └── lib/             API client, auth store, helpers
└── docs/
    ├── SPEC.md              Full project requirements and acceptance criteria
    ├── ARCHITECTURE.md      System architecture
    ├── AGENT_DOCS.md        AI agent inventory
    └── TEST_RECORDING.md    Sample call script for testing real transcription
```

---

## Getting started

### Prerequisites

- **Python 3.11+**
- **Node.js 20.9+** and npm
- **ffmpeg** for real transcription: `brew install ffmpeg` (macOS) or `winget install ffmpeg` (Windows)
- A free **Groq API key** from https://console.groq.com/keys (optional; the app runs in mock mode without one)

PostgreSQL and Redis are **not** required for local development.

### 1. Backend

```bash
cd backend
python3 -m venv venv

# macOS / Linux
./venv/bin/pip install fastapi "uvicorn[standard]" sqlalchemy alembic aiosqlite greenlet asyncpg psycopg2-binary \
  "python-jose[cryptography]" passlib bcrypt pydantic pydantic-settings email-validator openai tenacity \
  structlog celery redis aiofiles httpx python-slugify rich pypdf python-docx python-multipart chromadb

cp .env.local.example .env.local
```

On Windows (PowerShell), use `.\venv\Scripts\pip install ...` with the same packages and `Copy-Item .env.local.example .env.local`.

Open `backend/.env.local` and set your Groq key:

```bash
LLM_API_KEY="gsk_your_groq_key_here"
```

`.env.local` is ignored by git, so your key is never committed. Don't put real keys in `backend/.env`, which is tracked. To run without a key, set `LLM_PROVIDER="mock"` and `STT_PROVIDER="mock"`.

Start the backend:

```bash
./venv/bin/python start.py          # Windows: .\venv\Scripts\python start.py
```

This creates the database tables, loads the demo data, builds the search index and starts the API with auto-reload.

- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/api/docs

The first real search downloads the ~80 MB embedding model to `~/.cache/chroma`.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Open http://localhost:3000.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.talkwiseai.com | admin123 |
| Manager | manager@demo.talkwiseai.com | manager123 |
| Agent | agent@demo.talkwiseai.com | agent123 |

You can also create a new workspace from the **Create one** link on the login page.

### Try the full pipeline

Record the short script in `docs/TEST_RECORDING.md`, then upload it on the **Conversations** page. The "Expected results" table in that file shows what the analysis should find. A 1-minute call takes about 25 seconds to process with Groq.

---

## Configuration

Settings are read from `backend/.env` (committed placeholders), then `backend/.env.local` (your machine, git-ignored), then real environment variables, with later sources winning.

| Variable | Default in `.env.local.example` | Purpose |
|---|---|---|
| `DATABASE_URL` / `DATABASE_SYNC_URL` | `./storage/talkwiseai.db` (SQLite) | Async URL for the API, sync URL for scripts and the worker. Use `postgresql+asyncpg://...` / `postgresql://...` for Postgres |
| `LLM_PROVIDER` | `openai` | `openai` (any OpenAI-compatible API) or `mock` |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Leave empty for OpenAI itself |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Must be a model your key can use |
| `LLM_REASONING_EFFORT` | `low` | Only for reasoning models; leave empty otherwise |
| `LLM_API_KEY` | – | Your Groq (or OpenAI) key |
| `LLM_MAX_CONCURRENCY` | `3` | Parallel AI calls; keeps free-tier rate limits happy |
| `STT_PROVIDER` | `whisper_api` | `whisper_api` (hosted), `whisper_local` (needs `openai-whisper`), or `mock` |
| `STT_API_MODEL` | `whisper-large-v3-turbo` | Hosted Whisper model |
| `STT_MAX_UPLOAD_MB` | `25` | Larger recordings are compressed and split automatically |
| `EMBEDDING_PROVIDER` | `local` | `local` (ONNX, free), `openai`, or `mock` |
| `CRM_PROVIDER` | `mock` | Only the mock CRM adapter exists so far |

In **mock mode**, every upload returns the same sample transcript and analysis. The Copilot, email and report features show search excerpts or data-only drafts instead of AI-written text.

---

## Features

**Working**

- Sign in and sign up, organization workspaces, roles (admin, manager, agent)
- Upload audio or video (MP3, WAV, M4A, OGG, FLAC, MP4, MOV, ...) with live processing progress
- Transcription with timestamps, and AI speaker-role labelling (e.g. Sales Representative / Customer)
- AI analysis per conversation:
  - Summary, key topics, decisions and next steps
  - Sentiment, customer intent and pain points
  - Sales intelligence (lead score, purchase intent, deal health, buying signals) and objections
  - Action items, meeting minutes, recommendations and agent quality score
- CRM update proposals you can review, edit, approve or reject; approval writes through the CRM adapter and is audit-logged
- Follow-up email drafts you can edit, copy or open in your mail app; nothing is sent automatically
- **Ask AI** about a single conversation, and an organization-wide **AI Copilot** with cited sources
- Knowledge base: upload PDF, DOCX, TXT or MD files and ask questions about them
- Semantic search index that survives restarts
- Dashboard, sales pipeline, analytics, action items, team role management, reports with CSV export
- In-app notifications when processing finishes or fails
- Light, dark and system themes

**Mock or placeholder for now**

- TalkWisely PBX, CRM, calendar and email integrations use mock adapters (no real third-party APIs yet)
- The Leads and Meetings pages are placeholders
- The dashboard's trend badges and "Conversation Volume" chart show sample values
- Settings toggles aren't saved

---

## AI pipeline

Each uploaded recording goes through these steps:

1. **Transcription**: ffmpeg converts the audio to 16 kHz mono, then hosted Whisper transcribes it.
2. **Transcript cleaning**: speaker turns are labelled with roles based on what each person says.
3. **Classification**: conversation type and purpose.
4. **Parallel analysis** (8 agents at once):
   - Summary
   - Sentiment
   - Intent
   - Pain points
   - Sales intelligence
   - Objections
   - Entities
   - Action items
5. **Meeting minutes**, then **recommendations**, then **CRM proposals**, then **agent quality score**.
6. **Save and index**: results are validated against the database schema, stored, and indexed for search. A notification is sent when done.

Outside the pipeline, the **Copilot**, **follow-up email** and **executive report** agents answer on demand. All agents are told to separate facts from inferences and to reply "Not found in the available conversations." rather than invent details. See `docs/AGENT_DOCS.md` for the full agent list.

---

## Useful commands

```bash
# Backend (from backend/)
./venv/bin/python scripts/seed.py          # reload demo data (skips what already exists)
./venv/bin/python scripts/reindex.py       # index anything missing from search
./venv/bin/python scripts/reindex.py --all # rebuild the whole search index
./venv/bin/python tests/run_tests.py       # quick smoke tests (no pytest needed)

./venv/bin/pip install pytest pytest-asyncio pytest-cov
./venv/bin/pytest tests/ -v

# Frontend (from frontend/)
npm run lint
npx tsc --noEmit
npx shadcn@latest add <component>          # add a shadcn/ui component
```

---

## Known limitations

- **Demo data:** the 8 seeded conversations share placeholder summaries and transcripts, so Copilot answers about them aren't meaningful. Upload real recordings for realistic results.
- **Page reload:** reloading a dashboard page in the browser signs you out; navigating within the app works.
- **Speaker labels:** these come from the AI reading the conversation, not from voice recognition, so similar-sounding turns can be mislabelled.
- **AI accuracy:** AI output can still contain mistakes. Review CRM changes and emails before using them.
- **Not built yet:**
  - Docker setup
  - Database migrations (schema changes need a database reset)
  - AI evaluation dataset
  - End-to-end tests

---

## Documentation

- `docs/SPEC.md` — complete requirements and final acceptance criteria
- `docs/ARCHITECTURE.md` — system architecture
- `docs/AGENT_DOCS.md` — AI agents and safety rules
- `docs/TEST_RECORDING.md` — test call script and expected results
- `CLAUDE.md` — developer notes on architecture and conventions
- API reference — http://localhost:8000/api/docs (Swagger) and http://localhost:8000/api/redoc

---

*Academic project: Semester Group Project (10 credits), in collaboration with TalkWisely, Ahmedabad.*
