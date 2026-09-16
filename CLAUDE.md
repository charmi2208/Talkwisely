# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TalkWiseAI: an AI conversation-intelligence platform (call/meeting upload → transcription → multi-agent analysis → sales/meeting insights) built for the TalkWisely Cloud PBX ecosystem as a 10-credit college Semester Group Project (SGP). Two independent apps: `backend/` (FastAPI) and `frontend/` (Next.js). The top-level `talkwisely/` directory is empty apart from a `.gitattributes`.

## Product spec and context

- `docs/SPEC.md` is the master requirements spec (the prompt the project was originally generated from). Treat it as the source of truth for features, agents, pages, and the final acceptance criteria (§86). Everything centers on the **Conversation** entity (§78), and new work should be built in vertical slices (§83).
- `docs/TEST_RECORDING.md` is a short sales-call script with the expected analysis, for testing the upload pipeline with real providers. The course slides list this tech stack: React, FastAPI, LangGraph, Whisper, GPT/Claude, ChromaDB, PostgreSQL, JWT.
- Rules from the spec that apply to all changes:
  - Don't fake functionality or ship buttons that do nothing. Use mock adapters only where credentials or APIs are unavailable, and label them as mock.
  - Never invent TalkWisely (or other third-party) APIs; add an adapter interface plus a mock instead.
  - AI output must be structured and validated. Keep FACT vs INFERENCE vs RECOMMENDATION separate. When data is absent, say "Not found in the available conversation" and never invent dates, prices, people, decisions or CRM fields. Label QA scores as AI-generated assessments.
  - CRM updates and outgoing emails require explicit user approval. The LLM must never execute arbitrary SQL; use predefined analytics functions.
  - Every major entity is scoped by `organization_id`.

### Known gaps vs the spec

- **Real AI needs a key:** with `LLM_PROVIDER=mock` / `STT_PROVIDER=mock`, `MockSTTProvider` returns the same canned transcript for any upload and `MockLLMProvider` returns canned analysis. The Copilot, email and report agents detect mock mode and fall back to search excerpts or data-only templates instead of fake prose.
- **Speaker diarization:** hosted Whisper has none. `WhisperAPIProvider` guesses turns from pauses, and `node_clean_transcript` asks the LLM to label each line with a role (only when the LLM isn't mock).
- **Missing pieces:**
  - The `langgraph` library isn't actually used.
  - `require_roles` is only applied to `PATCH /users/{id}/role`.
  - No Docker/Compose files, no Alembic migrations, no evaluation dataset, and `tests/e2e/` is empty.
  - `KnowledgeDocument` has no `category` column; the category lives in the first `KnowledgeChunk.extra_metadata`.
- **Unfinished UI:** Leads and Meetings are placeholder pages, Settings switches aren't persisted, and the dashboard's trend badges and "Conversation Volume" chart are hardcoded sample values.
- **Mock-mode quirk:** a freshly uploaded file processed in mock mode can come back without `sales_insight` or recommendations, likely because of the prompt-keyword routing described under Backend architecture.

## Commands

### Backend (`backend/`, Python ≥3.11)

```bash
python3 -m venv venv
./venv/bin/pip install fastapi "uvicorn[standard]" sqlalchemy alembic aiosqlite greenlet asyncpg psycopg2-binary \
  "python-jose[cryptography]" passlib bcrypt pydantic pydantic-settings email-validator openai tenacity \
  structlog celery redis aiofiles httpx python-slugify rich pypdf python-docx python-multipart chromadb
cp .env.local.example .env.local             # then add the Groq key and switch providers

# Run: creates tables, seeds demo data, backfills the search index, starts uvicorn on :8000 (docs at /api/docs)
./venv/bin/python start.py

./venv/bin/python scripts/seed.py            # re-run seed only
./venv/bin/python scripts/reindex.py         # index conversations/KB docs missing from the vector store (--all rebuilds)
./venv/bin/python tests/run_tests.py         # standalone smoke suite (no pytest needed)
./venv/bin/pip install pytest pytest-asyncio pytest-cov   # pytest is not in the install list above
./venv/bin/pytest tests/ -v                  # asyncio_mode=auto is set in pyproject.toml
./venv/bin/pytest tests/unit/test_ai_pipeline.py::test_mock_llm_provider_completion
```

- The pip list above is the minimal runtime set. `pyproject.toml` also lists heavy optional deps (langchain, langgraph, openai-whisper, sentence-transformers, weasyprint) that the code imports lazily or not at all. `aiosqlite`, `greenlet` and `chromadb` are required but missing from `pyproject.toml`.
- **Settings:** pydantic-settings reads `backend/.env` (committed, placeholders only), then `backend/.env.local` (git-ignored, overrides it); real environment variables override both.
  - The committed `.env` points `DATABASE_URL` at a Windows path, so `.env.local` sets **both** `DATABASE_URL` (async, used by the API) and `DATABASE_SYNC_URL` (sync, used by `start.py`, seed, reindex and the pipeline worker) to `./storage/talkwiseai.db`.
  - Real API keys go only in `.env.local`, never in `.env`.
  - Postgres (`postgresql+asyncpg://…`) is the documented default; Redis is only needed if Celery is used.
- **Real AI (Groq free tier)**, all set in `.env.local` (see `.env.local.example`):
  - `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-120b`, `LLM_REASONING_EFFORT=low`, `LLM_API_KEY=gsk_…`
  - Free Groq keys don't have access to `llama-3.3-70b-versatile`. Check available models with the models list endpoint before changing `LLM_MODEL`. `LLM_REASONING_EFFORT` is only sent when set, because non-reasoning models reject it.
  - `STT_PROVIDER=whisper_api`, which reuses the LLM key and base URL
  - `EMBEDDING_PROVIDER=local`: ONNX all-MiniLM-L6-v2 from chromadb, downloaded (~80 MB) to `~/.cache/chroma` on first use
- Test vectors: `tests/conftest.py` (pytest) and `tests/run_tests.py` point `CHROMA_PERSIST_DIR` at a temp dir, so tests never write to the real `vector_store/`. The integration tests use `httpx.ASGITransport`, because httpx 0.28 removed `AsyncClient(app=...)`.
- No Alembic migrations exist; schema is created with `Base.metadata.create_all` in `start.py` / `seed.py`. Model changes to existing tables need a manual DB reset.
- Demo logins (seeded): `admin@demo.talkwiseai.com` / `admin123`, `manager@…` / `manager123`, `agent@…` / `agent123`.

### Frontend (`frontend/`)

```bash
npm install --legacy-peer-deps
npm run dev        # next dev --webpack on :3000
npm run lint       # eslint (flat config); the repo already has many pre-existing errors
npx tsc --noEmit   # currently clean
npx shadcn@latest add <component>   # UI components land in src/components/ui
```

- Next.js is 16.x with breaking changes; per `frontend/AGENTS.md`, read `node_modules/next/dist/docs/` before writing Next-specific code.
- API base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`).

## Backend architecture

- `app/main.py` mounts every router in `app/api/v1/*` under `/api/v1` (each router sets its own prefix, e.g. `/conversations`, `/ai`, `/sales`). Health check: `GET /health`.
- **Auth / tenancy:** `core/dependencies.py` exposes `get_current_user` (Bearer JWT → active `User`) and `require_roles(...)`. Multi-tenancy is manual: queries must filter by `current_user.organization_id`. Models use string UUID primary keys (`db/models/models.py`).
  - Roles live in `user_roles` → `roles`; `User` has no `role` field. `api/v1/users.py` resolves a primary role (admin > manager > agent).
- **Upload → analysis flow:**
  1. `POST /conversations/upload` saves the file to `storage/uploads/<organization_id>/` and creates `Conversation` and `ProcessingJob` rows.
  2. It schedules `workers/conversation_tasks.run_conversation_pipeline_direct` via FastAPI `BackgroundTasks`, not Celery. `workers/celery_app.py` exists but the API doesn't use it.
  3. The worker uses a **sync** SQLAlchemy session plus `asyncio.run`. It runs STT, stores speakers and transcript segments, and runs `ConversationPipeline`. It then writes the LLM speaker roles back onto the segments, persists every insight table, indexes the conversation for search (`ai/rag/indexer.py`), and creates a notification.
  4. It updates `ProcessingJob.progress`/`current_step`, which the frontend polls via `GET /conversations/{id}/processing-status`.
  5. Deleting a conversation also deletes its vectors.
- **Pipeline:** `ai/pipeline/graph.py` is described as LangGraph but is plain asyncio.
  - Nodes in `ai/pipeline/nodes.py` have the signature `async (state, llm) -> partial-state dict` and share the `ConversationState` TypedDict (`state.py`).
  - Order: clean_transcript → classify → 8 analysis nodes run in parallel via `asyncio.gather(return_exceptions=True)`, where failures are appended to `state["errors"]` → meeting minutes → recommendations → CRM proposals → agent score.
  - Nodes must not touch the DB; persistence happens after the graph finishes.
  - AI output is untyped. Before saving, the worker runs `db/sanitize.py::clean_row` on every new row, which coerces values to column types (e.g. `"00:48"` becomes 48.0, `"85/100"` becomes 85), trims strings, lowercases enum columns and applies scalar defaults for nulls. A single bad value once failed the whole insert.
  - On failure the worker rolls back first, then stores a user-facing message (`_user_facing_error`) and logs the full traceback.
  - Close HTTP-based providers inside the loop that created them. The worker calls `_close_provider`, and API routes use `async with llm_session() as llm` from `graph.py`. Otherwise you get "Event loop is closed" tracebacks.
- **Providers:** `ai/providers/base.py` defines the `LLMProvider`, `SpeechToTextProvider` and `EmbeddingProvider` ABCs.
  - `get_llm_provider()` / `get_stt_provider()` in `graph.py` choose providers from settings: `openai` (any OpenAI-compatible API) or `mock` for the LLM; `whisper_api`, `whisper_local` or `mock` for speech-to-text. `get_embedding_provider()` in `ai/providers/embedding/__init__.py` chooses `local`, `openai` or `mock`. Everything defaults to mock.
  - **LLM provider:** `OpenAILLMProvider` caps parallel calls with a semaphore (`LLM_MAX_CONCURRENCY`). It retries only rate limits, transport/5xx errors and Groq `json_validate_failed`; `complete_json` re-asks once on invalid JSON.
  - **Hosted Whisper:** `WhisperAPIProvider` converts audio to 16 kHz mono MP3 with ffmpeg (which also extracts audio from video) and splits files over `STT_MAX_UPLOAD_MB` into 10-minute parts.
  - `MockLLMProvider` chooses its canned response by **keywords in the prompt** (`copilot`, `classif`, `summar`, `sentiment`, `objection`, …). Rewording a node's prompt can silently change which mock response it gets.
- **RAG:**
  - **Vector store:** `ai/rag/vector_store.py` uses the configured embedding provider and persistent ChromaDB (`vector_store/`). Each embedding model gets its own collection (`talkwise_rag_<provider>`), so switching providers needs `scripts/reindex.py`. Without chromadb it falls back to an in-memory store that's lost on restart.
  - **Filters:** multi-field filters need `$and` (use the `_where` helper), and every search is scoped by `organization_id`.
  - **What gets indexed:** `ai/rag/indexer.py` indexes transcript windows (with speaker and timestamp) plus a summary chunk per conversation. Knowledge-base uploads extract PDF/DOCX/TXT text, store the chunks in `knowledge_chunks` and embed them.
  - **Copilot:** `ai/agents/copilot_agent.py` combines vector hits (numbered sources, returned as `citations`) with database records: a single conversation's summary, sales signals, tasks and objections, or an org-wide index of recent conversations.
    - Only the sources the answer actually cites (`[n]`) are returned. Full-width `【n】` markers are normalized to `[n]`.
  - **Other agents:** email and report agents live in `ai/agents/`. Reports use period-scoped metrics from `api/v1/reports.py::_collect_metrics`.
- `integrations/*` are adapter classes (TalkWisely PBX, CRM, calendar, email) that default to mock mode.
  - **CRM:** changes are proposals. `POST /crm/proposals/{id}/approve` writes through `get_crm_provider()`, which only implements mock so far. It then sets `status=applied`, `approved_by` and `applied_at`, and adds an audit log entry.

## Frontend architecture

- App Router, every page is a client component. `src/app/(auth)/login` and `/register` are public (they share `components/auth/AuthBrandPanel`). `src/app/(dashboard)/layout.tsx` guards all other routes using the persisted zustand store `lib/stores/authStore.ts` (localStorage key `talkwiseai-auth`, tokens also in `access_token` / `refresh_token`).
  - Known bug: the guard runs before zustand rehydrates, so a hard reload of any dashboard route bounces to `/login`.
- Each page wraps its content in `components/layout/AppShell` (`title`/`subtitle` props), which renders the shadcn `Sidebar` nav and a header with the theme toggle and `NotificationsMenu` (a popover that polls `/notifications` every 60s).
- The conversation detail page adds `components/conversation/*`: `FollowUpEmailDialog` (draft, edit, copy or open in the mail app; never auto-sent), `CrmProposalsPanel` (review, edit, approve or reject) and `ConversationChat` (per-conversation Copilot with sources).
- `lib/api/client.ts` is an axios instance that attaches the Bearer token; any 401 clears auth and redirects to `/login`. Thin typed wrappers live in `lib/api/*.ts`, but many pages call `apiClient` directly. Use `lib/api/errors.ts::apiErrorMessage` to show FastAPI error details. Parse backend timestamps with `lib/dates.ts::parseApiDate`: the API sends naive UTC without an offset, so `new Date()` would read it as local time. Downloads must go through `apiClient` (e.g. `responseType: "blob"`), because `window.open` can't send the token.
- Several pages (sales, action items, knowledge base, integrations, analytics, team, reports) fall back to **hardcoded demo data in `catch` blocks** when an API call fails. A page showing data does not mean the endpoint works.

### UI conventions (user preferences)

These supersede an earlier redesign brief, which asked for an indigo primary and light mode only. Keep its intent: a calm, professional B2B look with no glow, neon or decorative gradients, and status never conveyed by color alone.

- Every UI element should be a shadcn/ui component. The project uses `components.json` with style `radix-vega`, the unified `radix-ui` package, and `cn` imported from the `cn` package. Prefer `Item`, `Empty`, `Field`, `Spinner`, `InputGroup`, `ToggleGroup`, `AlertDialog` (for destructive confirms) over hand-styled markup. Toasts use `sonner`.
- No emojis anywhere in the UI, including backend mock/AI text that reaches the UI.
- Restyling requests mean "change the look, not the content or behavior."
- Theme: shadcn preset with base `mist`, theme and charts `cyan`, font Inter (`--font-inter`), light/dark/system via `next-themes` (`components/theme-provider.tsx`, `components/mode-toggle.tsx`). Tokens live in `src/app/globals.css`, including custom `--success`, `--warning` and `--brand-panel(-foreground)` tokens.
  - Use `text-success` / `text-warning` / `bg-brand-panel` rather than raw emerald/amber/primary classes so both modes keep ≥4.5:1 text contrast.
  - Charts use shadcn `ChartContainer` with `theme: { light, dark }` colors when a series needs a different shade per mode.
