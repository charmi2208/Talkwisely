# TalkWiseAI

**AI-Powered Meeting, Call & Sales Intelligence Platform**

TalkWiseAI turns recorded sales calls, support calls and meetings into structured business intelligence: transcripts with speaker roles, summaries, sentiment, customer intent, lead scores, objections, action items, meeting minutes, CRM update proposals and agent quality scores. Everything is searchable, an AI Copilot answers questions with cited sources, and managers get team analytics and reports.

Built for the TalkWisely (Ahmedabad) Cloud PBX ecosystem as a 10-credit Semester Group Project (SGP).

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui, light and dark mode |
| Backend | FastAPI, SQLAlchemy 2 (async), Pydantic, Alembic migrations, JWT authentication with role-based access |
| AI pipeline | LangGraph `StateGraph` with 14 agents; 8 analysis agents run in parallel; schema-validated JSON output |
| LLM | Any OpenAI-compatible API. Default: Groq `openai/gpt-oss-120b` (free tier) |
| Speech-to-text | Hosted Whisper (`whisper-large-v3-turbo` on Groq) with ffmpeg preprocessing; local Whisper optional |
| Semantic search | ChromaDB with local ONNX embeddings (all-MiniLM-L6-v2, no API key) |
| Database | SQLite for local development and tests; PostgreSQL in Docker and production |
| Background jobs and caching | In-process jobs and memory cache by default; Celery and Redis optional |
| Integrations | Adapter interfaces with mock implementations for TalkWisely PBX, CRM, calendar and email |

---

## Quick start

### Docker

```bash
docker compose up --build
```

Open http://localhost:3000 (API docs: http://localhost:8000/api/docs). AI runs in mock mode until you add keys to `backend/.env.local`.

### Local development

```bash
# Backend (Python 3.11+)
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
cp .env.local.example .env.local       # add your Groq key, or set LLM_PROVIDER/STT_PROVIDER to "mock"
./venv/bin/python start.py             # migrates, seeds demo data, indexes, serves on :8000

# Frontend (Node 20.9+), in a second terminal
cd frontend
npm install --legacy-peer-deps
npm run dev                            # http://localhost:3000
```

Full instructions, Windows commands and every environment variable: [docs/SETUP.md](docs/SETUP.md).

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.talkwiseai.com | admin123 |
| Manager | manager@demo.talkwiseai.com | manager123 |
| Agent | agent@demo.talkwiseai.com | agent123 |

To try the full pipeline with real AI, record the script in [docs/TEST_RECORDING.md](docs/TEST_RECORDING.md) and upload it on the **Conversations** page.

---

## Features

- **Accounts and roles:** sign up, sign in, forgot and reset password, change password, organization workspaces. Admins manage the team (add members, change roles, deactivate accounts); agents see only their own conversations.
- **Ingestion:** upload audio or video with live progress, import calls from the TalkWisely PBX adapter (manual sync or scheduled auto-sync), or import recordings from meeting platforms.
- **Transcription:** timestamps, AI speaker-role labelling, editable speaker names and talk-time per speaker.
- **AI analysis per conversation:**
  - Summary, key topics, decisions and next steps
  - Sentiment, customer intent and pain points
  - Sales intelligence (lead score, purchase intent, deal health, buying signals) and objections
  - Competitors and other entities
  - Action items, meeting minutes, recommendations and an AI quality score for the agent
- **Human in the loop:** CRM update proposals you review, edit, approve or reject; follow-up email drafts that are never sent automatically.
- **Search and Copilot:** ask about one conversation or across all of them and the knowledge base, with cited sources. Analytics questions ("What percentage of calls were positive?") get exact numbers from predefined queries.
- **Work management:** action items with owners, due dates, priorities and overdue tracking; leads and an eight-stage sales pipeline; meetings with downloadable minutes.
- **Analytics and reports:** dashboard and analytics with date, type and team-member filters and period-over-period changes; executive, conversation, sales, agent performance, sentiment and objection reports, saved and downloadable as PDF, CSV or Markdown.
- **Operations:** notifications, preferences that change behavior, integration settings, audit log, rate limiting, caching (in memory or Redis), reprocessing.

### What is mocked

- The TalkWisely PBX, meeting platform, CRM, calendar and email integrations use mock adapters, because the real APIs aren't available to this project. The Integrations page labels them as mocks.
- Without an AI key, mock mode returns the same sample transcript and analysis for every upload.

---

## How the analysis works

```
upload -> speech-to-text -> LangGraph pipeline -> validate & store -> index for search -> notify

pipeline:  validate_input -> clean_transcript -> classify
           -> summarize | sentiment | intent | pain_points | sales_intelligence | objections | entities | action_items
           -> aggregate -> meeting_minutes -> crm_update -> recommendations -> agent_score
```

Each agent returns JSON that is validated against its schema before storage; unknown values are stored as null rather than guessed. On a small hand-labelled evaluation set with Groq `openai/gpt-oss-120b`, the pipeline classified conversation type and intent correctly in all six calls and reached F1 scores of 84% for objections, 89% for competitors and 80% for action items. Details: [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) and [backend/evaluation/README.md](backend/evaluation/README.md).

---

## Project structure

```
Talkwisely/
├── backend/
│   ├── app/                 FastAPI app (api, ai, core, db, integrations, services, workers)
│   ├── alembic/             Database migrations
│   ├── evaluation/          AI evaluation dataset, runner and results
│   ├── scripts/             seed.py, reindex.py, generate_docs.py
│   ├── tests/               unit, integration and end-to-end tests
│   ├── start.py             Local dev server (migrate, seed, index, serve)
│   └── Dockerfile
├── frontend/
│   ├── src/app/             Pages: (auth) and (dashboard)
│   ├── src/components/      shadcn/ui and app components
│   ├── src/lib/             Typed API modules, auth store, helpers
│   └── Dockerfile
├── docs/                    Documentation (below)
├── docker-compose.yml       PostgreSQL + API + web app
└── docker-compose.celery.yml  Adds Redis, Celery workers and a Chroma server
```

---

## Useful commands

```bash
# Backend (from backend/)
./venv/bin/pytest                            # all tests (mock providers, throwaway database)
./venv/bin/python -m app.db.migrate          # apply migrations
./venv/bin/python scripts/seed.py            # reload demo data
./venv/bin/python scripts/reindex.py --all   # rebuild the search index
./venv/bin/python -m evaluation.run_eval     # AI evaluation (needs a real model)
./venv/bin/python scripts/generate_docs.py   # refresh docs/API.md and docs/DATABASE.md

# Frontend (from frontend/)
npx tsc --noEmit
npm run lint
npm run build
npm run test:e2e                             # browser tests (needs Chrome and backend/venv)
```

---

## Documentation

| Document | Contents |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Requirements and final acceptance criteria |
| [docs/SETUP.md](docs/SETUP.md) | Setup guide and environment variables |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Using the app, page by page and by role |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, data flow, security |
| [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | LangGraph pipeline, validation, providers, search, evaluation results |
| [docs/AGENT_DOCS.md](docs/AGENT_DOCS.md) | The 17 agents and their safety rules |
| [docs/API.md](docs/API.md) | Every endpoint and who may call it (also live at `/api/docs`) |
| [docs/DATABASE.md](docs/DATABASE.md) | Tables, columns and relationships |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Adapters, PBX import, CRM approval, adding real providers |
| [docs/TESTING.md](docs/TESTING.md) | Test suite and how to run it |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment topology and production checklist |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Conventions, adding agents and endpoints, migrations |
| [docs/TEST_RECORDING.md](docs/TEST_RECORDING.md) | Test call script with expected results |

---

## Known limitations

- **Speaker labels** come from pauses in the audio and the AI reading the conversation, not from voice recognition. Rename speakers when they're wrong.
- **Demo data:** the seeded conversations share placeholder transcripts, so Copilot answers about them aren't meaningful. Upload real recordings for realistic results.
- **AI accuracy:** results can contain mistakes (purchase intent was the weakest task in evaluation). Review CRM changes and emails before using them.
- **Integrations** are mock adapters until real provider APIs are connected.
- **Scale:** for several API replicas, use Celery, a Chroma server and `CACHE_BACKEND=redis` (shared cache and rate limits); the Celery compose override sets all three.

---

*Academic project: Semester Group Project (10 credits), in collaboration with TalkWisely, Ahmedabad.*
