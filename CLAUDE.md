# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TalkWiseAI: an AI conversation-intelligence platform (call/meeting upload → transcription → multi-agent analysis → sales/meeting insights) built for the TalkWisely Cloud PBX ecosystem as a 10-credit college Semester Group Project (SGP). Two independent apps: `backend/` (FastAPI) and `frontend/` (Next.js). The top-level `talkwisely/` directory is empty apart from a `.gitattributes`. User-facing docs live in `docs/` (setup, user guide, architecture, AI architecture, API, database, integrations, testing, deployment, developer guide).

## Product spec and context

- `docs/SPEC.md` is the master requirements spec (the prompt the project was originally generated from). Treat it as the source of truth for features, agents, pages, and the final acceptance criteria (§86). Everything centers on the **Conversation** entity (§78), and new work should be built in vertical slices (§83).
- `docs/TEST_RECORDING.md` is a short sales-call script with the expected analysis, for testing the upload pipeline with real providers. The course slides list this tech stack: React, FastAPI, LangGraph, Whisper, GPT/Claude, ChromaDB, PostgreSQL, JWT.
- Rules from the spec that apply to all changes:
  - Don't fake functionality or ship buttons that do nothing. Use mock adapters only where credentials or APIs are unavailable, and label them as mock. Pages must never fall back to sample data when an API call fails; show `ErrorState` instead.
  - Never invent TalkWisely (or other third-party) APIs; add an adapter interface plus a mock instead.
  - AI output must be structured and validated. Keep FACT vs INFERENCE vs RECOMMENDATION separate. When data is absent, say "Not found in the available conversation" and never invent dates, prices, people, decisions or CRM fields. Label QA scores as AI-generated assessments.
  - CRM updates and outgoing emails require explicit user approval. The LLM must never execute arbitrary SQL; use predefined analytics functions.
  - Every major entity is scoped by `organization_id`, and agents only see conversations they uploaded (see Auth below).

### Known limitations

- **Real AI needs a key:** with `LLM_PROVIDER=mock` / `STT_PROVIDER=mock`, `MockSTTProvider` returns the same canned sales-call transcript for any upload and `MockLLMProvider` returns canned analysis (chosen by the agent's `task` name). The Copilot, email and report agents detect mock mode and fall back to search excerpts or data-only templates instead of fake prose.
- **Speaker diarization:** hosted Whisper has none. `WhisperAPIProvider` guesses turns from pauses, `node_clean_transcript` asks the LLM to label each line with a role (only when the LLM isn't mock), and users can rename labels (`PATCH /conversations/{id}/speaker-labels`).
- **Integrations are mocks:** only mock PBX/CRM/calendar/email adapters exist. PBX import only works with `STT_PROVIDER=mock` because the mock PBX has no real audio.
- **Not verified here:** Docker images and the PostgreSQL path haven't been run on this machine (no Docker/Postgres installed); the Postgres migration SQL was generated offline with `alembic upgrade head --sql`.
- **Scale:** multi-replica deployments need `TASK_QUEUE=celery`, `CHROMA_HOST` and `CACHE_BACKEND=redis` (shared cache and rate limits); `docker-compose.celery.yml` sets all three.

## Commands

### Backend (`backend/`, Python ≥3.11)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt   # pinned, tested versions (requirements.txt = runtime only)
cp .env.local.example .env.local                 # then add the Groq key and switch providers

# Run: applies Alembic migrations, seeds demo data, backfills the search index, starts uvicorn on :8000 (docs at /api/docs)
./venv/bin/python start.py

./venv/bin/python -m app.db.migrate          # migrations only
./venv/bin/python scripts/seed.py            # re-run seed only (also migrates)
./venv/bin/python scripts/reindex.py         # index conversations/KB docs missing from the vector store (--all rebuilds)
./venv/bin/python scripts/generate_docs.py   # regenerate docs/API.md and docs/DATABASE.md after route/model changes
./venv/bin/pytest                            # full suite: unit, integration, API-level e2e (~1 min)
./venv/bin/pytest tests/unit/test_pipeline_graph.py::test_full_run_completes_every_step
./venv/bin/python -m evaluation.run_eval     # AI evaluation with the configured real model (refuses mock unless --allow-mock)
./venv/bin/python tests/run_tests.py         # old standalone smoke script (uses your real embedding settings)
```

- **Settings:** pydantic-settings reads `backend/.env` (committed, placeholders only), then `backend/.env.local` (git-ignored, overrides it); real environment variables override both. Full variable reference: `docs/SETUP.md`.
  - The committed `.env` points `DATABASE_URL` at a Windows path, so `.env.local` sets **both** `DATABASE_URL` (async, used by the API) and `DATABASE_SYNC_URL` (sync, used by migrations, seed, reindex and the worker) to `./storage/talkwiseai.db`.
  - Real API keys go only in `.env.local`, never in `.env`.
  - Postgres (`postgresql+asyncpg://…`) is the documented default and what Docker uses. Redis is only needed with `TASK_QUEUE=celery`.
- **Real AI (Groq free tier)**, all set in `.env.local` (see `.env.local.example`):
  - `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-120b`, `LLM_REASONING_EFFORT=low`, `LLM_API_KEY=gsk_…`
  - Free Groq keys don't have access to `llama-3.3-70b-versatile`. Check available models with the models list endpoint before changing `LLM_MODEL`. `LLM_REASONING_EFFORT` is only sent when set, because non-reasoning models reject it.
  - `STT_PROVIDER=whisper_api`, which reuses the LLM key and base URL
  - `EMBEDDING_PROVIDER=local`: ONNX all-MiniLM-L6-v2 from chromadb, downloaded (~80 MB) to `~/.cache/chroma` on first use
- **Tests:** `tests/conftest.py` sets env vars before the app is imported: throwaway SQLite DB (migrated + seeded once per session), temp storage and vectors, mock LLM/STT/embeddings regardless of `.env.local`, rate limiting off. pytest-asyncio runs everything on one session-scoped loop (`pyproject.toml`) because the async engine is created at import. Uploads in tests run the real background job (httpx `ASGITransport` awaits it), so insights are readable right after `upload()`.
- **Migrations:** Alembic (`alembic/`, `alembic.ini`); `app/db/migrate.py::upgrade_database()` stamps pre-Alembic databases (tables but no `alembic_version`) at `0001` and upgrades to head. After model changes: `./venv/bin/alembic revision --autogenerate -m "..."`, name constraints explicitly (SQLite uses batch mode), guard data backfills with `op.get_context().as_sql`, then `alembic check` should be clean.
- **Browser e2e:** `cd frontend && npm run test:e2e` (Playwright 1.65.0 pinned, system Chrome via `channel: "chrome"`). `playwright.config.ts` starts `backend/scripts/e2e_server.py` (temp DB, demo data, mock AI) on :8020 and a production build (`npm run build && next start`) on :3020; dev-server compiles were too slow and flaky. Stop `next dev` first (shared `.next`). Specs live in `frontend/e2e/`; `helpers.ts::login` retries the quick-fill until hydration because the login page is server-rendered (its demo buttons' text is lowercase).
- **Docker:** `docker compose up --build` (Postgres + API + web, in-process jobs); add `-f docker-compose.celery.yml` for Redis, Celery worker and a Chroma server. The backend entrypoint migrates, seeds and reindexes unless `RUN_MIGRATIONS=false` / `SEED_DEMO_DATA=false`.
- Demo logins (seeded): `admin@demo.talkwiseai.com` / `admin123`, `manager@…` / `manager123`, `agent@…` / `agent123`, `agent2@…` / `agent123`.

### Frontend (`frontend/`)

```bash
npm install --legacy-peer-deps
npm run dev        # next dev --webpack on :3000
npm run build      # next build --webpack (Next 16 defaults to Turbopack, which rejects the webpack config)
npm run lint       # eslint (flat config); remaining errors are mostly no-explicit-any in older files and set-state-in-effect on fetch-on-mount
npx tsc --noEmit   # currently clean
npx shadcn@latest add <component>   # UI components land in src/components/ui
```

- Next.js is 16.x with breaking changes; per `frontend/AGENTS.md`, read `node_modules/next/dist/docs/` before writing Next-specific code (e.g. `useSearchParams` needs a `<Suspense>` boundary, as in `reset-password`).
- API base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`), compiled into the build.

## Backend architecture

- `app/main.py` mounts every router in `app/api/v1/*` under `/api/v1` (each router sets its own prefix). Health check: `GET /health`. It also installs the rate-limit middleware and, outside `APP_ENV=test`, starts the PBX auto-sync loop (`services/scheduler.py`). This FastAPI version registers routers lazily, so count endpoints via `app.openapi()`, not `app.routes`.
- **Auth / tenancy:** `core/dependencies.py::get_current_user` (Bearer JWT → active `User`, with `user_roles` eager-loaded) and `require_roles(...)`. `core/access.py` has `primary_role`, `is_privileged` (admin/manager) and `conversation_scope(user)`: always use `*conversation_scope(current_user)` in `where()` for conversation-derived data; it adds `created_by == user.id` for agents. Action items use `visible_action_items(user)` (manual tasks have no conversation; agents see their own).
  - Roles live in `user_roles` → `roles`; `User` has no `role` field. Admin-only: user management, integration config, KB upload/delete, audit log. Admin+manager: team list, reports, PBX sync, integration tests, AI settings.
  - Password reset: `core/security.py` tokens embed a fingerprint of the current hash, so they're single-use; in development with the mock email provider `/auth/forgot-password` returns `dev_reset_url`.
- **Upload → analysis flow:**
  1. `POST /conversations/upload` saves the file to `storage/uploads/<organization_id>/` and creates `Conversation` and `ProcessingJob` rows.
  2. `workers/conversation_tasks.enqueue_conversation_processing` runs `run_conversation_pipeline_direct` via FastAPI `BackgroundTasks` (default), a daemon thread (scheduled jobs, no request), or the Celery task `process_conversation` (`TASK_QUEUE=celery`). All paths share one implementation and error handling.
  3. The worker uses a **sync** SQLAlchemy session plus `asyncio.run`. It runs STT, stores speakers and transcript segments, and runs `ConversationPipeline`. If the graph returns `status == "failed"` it raises `PipelineError` (user-facing message). Otherwise it writes LLM speaker roles back onto the segments, persists every insight table (respecting the uploader's `auto_action_items` preference), indexes the conversation (`ai/rag/indexer.py`), audit-logs, and creates notifications (completion, plus a high-intent alert for lead score ≥ 80 if `lead_intent_alerts`).
  4. It updates `ProcessingJob.progress`/`current_step`, which the frontend polls via `GET /conversations/{id}/processing-status`.
  5. Deleting a conversation also deletes its CRM records (no ORM cascade) and vectors. `POST /conversations/{id}/reprocess` clears results and re-runs.
- **Pipeline:** `ai/pipeline/graph.py` builds a real LangGraph `StateGraph` per run (`build_graph(llm, report)`): validate_input → clean_transcript → classify → 8 parallel analysis nodes (`ANALYSIS_NODES`) → aggregate (fan-in) → `POST_ANALYSIS_STEPS` (meeting_minutes → crm_update → recommendations → agent_score). Conditional edges route to END when a sequential step sets `status="failed"`; parallel-node exceptions are appended to `errors` instead.
  - Nodes in `ai/pipeline/nodes.py` have the signature `async (state, llm) -> partial-state dict` and must not touch the DB. `steps_completed`/`errors` are append reducers and `current_step` keeps the latest (`state.py`), so nodes return deltas (`"steps_completed": ["x"]`), never `state[...] + [...]`.
  - `_safe_call_agent` appends the shared `OUTPUT_RULES` to every system prompt, calls `llm.complete_json(messages, task=agent_name)`, then `ai/schemas/agent_outputs.py::validate_output(task, raw)` parses into the agent's Pydantic schema, repairs values ("85/100", "01:23", "High"), nulls "unknown" phrases and reports issues. Nodes only see the clean dict (every schema field present).
  - Before saving, the worker still runs `db/sanitize.py::clean_row` on every new row as a last safety net.
  - Close HTTP-based providers inside the loop that created them. The worker calls `_close_provider`, and API routes use `async with llm_session() as llm` from `graph.py`. Otherwise you get "Event loop is closed" tracebacks.
- **Providers:** `ai/providers/base.py` defines the `LLMProvider` (`complete`, `complete_json(..., task=None)`), `SpeechToTextProvider` and `EmbeddingProvider` ABCs.
  - `get_llm_provider()` / `get_stt_provider()` in `graph.py` choose providers from settings: `openai` (any OpenAI-compatible API) or `mock` for the LLM; `whisper_api`, `whisper_local` or `mock` for speech-to-text. `get_embedding_provider()` in `ai/providers/embedding/__init__.py` chooses `local`, `openai` or `mock`. Everything defaults to mock.
  - **LLM provider:** `OpenAILLMProvider` caps parallel calls with a semaphore (`LLM_MAX_CONCURRENCY`). It retries only rate limits, transport/5xx errors and Groq `json_validate_failed`; `complete_json` re-asks once on invalid JSON.
  - **Hosted Whisper:** `WhisperAPIProvider` converts audio to 16 kHz mono MP3 with ffmpeg (which also extracts audio from video) and splits files over `STT_MAX_UPLOAD_MB` into 10-minute parts.
  - `MockLLMProvider.complete_json` routes by `task` via `_TASK_GENERATORS` (keyword routing on the prompt is only a fallback for callers without a task). New agents need an entry there, and its output must pass the agent's schema (`tests/unit/test_agent_schemas.py`).
- **RAG:**
  - **Vector store:** `ai/rag/vector_store.py` uses the configured embedding provider and Chroma: persistent on disk (`vector_store/`) or a server when `CHROMA_HOST` is set. Each embedding model gets its own collection (`talkwise_rag_<provider>`), so switching providers needs `scripts/reindex.py`. Without chromadb it falls back to an in-memory store that's lost on restart.
  - **Filters:** multi-field filters need `$and` (use the `_where` helper), and every search is scoped by `organization_id`.
  - **What gets indexed:** `ai/rag/indexer.py` indexes transcript windows (with speaker and timestamp) plus a summary chunk per conversation. Knowledge-base uploads extract PDF/DOCX/TXT text, store the chunks in `knowledge_chunks` and embed them; `KnowledgeDocument.category` is a column (migration 0002).
  - **Copilot:** `ai/agents/copilot_agent.py` combines vector hits (numbered sources, returned as `citations`) with database records: a single conversation's summary, sales signals, tasks and objections, or an org-wide index of recent conversations. `owner_id` (set for agents) limits conversation hits and the index to that user's uploads; KB docs stay visible.
    - Only the sources the answer actually cites (`[n]`) are returned. Full-width `【n】` markers are normalized to `[n]`.
  - **Other agents:** email and report agents live in `ai/agents/`. Reports use period-scoped metrics from `api/v1/reports.py::_collect_metrics`, are saved in `reports`, and download as PDF (`services/report_export.py`, fpdf2 with Latin-1 sanitizing), CSV or Markdown.
- **Analytics:** `api/v1/analytics.py` endpoints share `AnalyticsFilters` (`days`, `conversation_type`, `agent_id` for privileged users) and compare against the previous period of the same length. Each is wrapped in `@cached(name)`. Postgres returns `Decimal` from `avg()`; wrap in `float()` (`_round`).
- **Natural-language analytics:** `services/nl_analytics.py` answers count/ranking/percentage questions with 10 predefined query functions (`TOOLS`). `route_by_rules` (regexes; ambiguous topics need an `ANALYTIC_CUES` word) runs first; only if it misses and the question looks analytical does a real LLM pick a tool/period/type from closed lists (`_RouterOutput` validation). Answer text and table come from the query results. The Copilot route tries this first when there's no `conversation_id` (`CopilotChatResponse.analytics`), as does `POST /ai/natural-language-query`.
- **Caching:** `core/cache.py` (`CACHE_BACKEND` memory/redis/none). Keys include the org's generation; a SQLAlchemy `after_flush`/`after_commit` hook on `Session` (installed from `db/session.py`) collects `obj.__dict__['organization_id']` of written rows and bumps those generations, so any commit touching org data invalidates its cached analytics/Copilot answers. New tables that hold org data without an `organization_id` column only invalidate if the same commit also writes an org-owned row (e.g. an `AuditLog`). Job progress is cached for `processing-status` (used only when the cached conversation status matches the DB). With redis, `core/rate_limit.py` uses `RedisRateLimitStore`.
- **Integrations:** `integrations/registry.py` declares each integration (talkwisely, meetings, crm, calendar, email; providers with availability, non-secret `ConfigField`s) and `get_integration()` creates per-org `Integration` rows with mock defaults. `services/recording_import.py::_import_recordings` imports PBX calls and meeting recordings (`POST /integrations/{key}/sync`; dedupe by stored file name, e.g. `talkwisely-<call_id>.opus`, `meeting-<recording_id>.m4a`). CRM approval (`POST /crm/proposals/{id}/approve`) checks the CRM integration is enabled, writes through `get_crm_provider(integration)`, sets `status=applied`, `approved_by`, `applied_at`, and audit-logs.
- **Preferences:** `core/preferences.py` (`auto_action_items`, `lead_intent_alerts`, `pbx_auto_sync`) stored in `User.preferences`; each one changes behavior in the worker or scheduler.
- **Evaluation:** `evaluation/dataset.json` (6 labelled conversations), `evaluation/run_eval.py` (accuracy, P/R/F1, summary fact recall, schema validity via a wrapped `validate_output`), results in `evaluation/results/`.

## Frontend architecture

- App Router, every page is a client component. `src/app/(auth)/login`, `/register`, `/forgot-password` and `/reset-password` are public (they share `components/auth/AuthBrandPanel`). `src/app/(dashboard)/layout.tsx` guards all other routes using the persisted zustand store `lib/stores/authStore.ts` (localStorage key `talkwiseai-auth`, tokens also in `access_token` / `refresh_token`). It waits for `useAuthHydrated()` (a `useSyncExternalStore` over zustand persist) before redirecting, then refreshes the profile from `/auth/me`.
- `useRole()` / `primaryRole()` give admin > manager > agent; `AppShell` filters nav items by `roles` (Team is admin/manager). Hide actions by role in the UI, but the API enforces access.
- Each page wraps its content in `components/layout/AppShell` (`title`/`subtitle` props), which renders the shadcn `Sidebar` nav and a header with the theme toggle and `NotificationsMenu` (a popover that polls `/notifications` every 60s).
- The conversation detail page adds `components/conversation/*`: `FollowUpEmailDialog` (draft, edit, copy or open in the mail app; never auto-sent), `CrmProposalsPanel` (review, edit, approve or reject) and `ConversationChat` (per-conversation Copilot with sources), plus Reprocess, speaker renaming and talk-time stats.
- `lib/api/client.ts` is an axios instance that attaches the Bearer token. On a 401 from a non-`/auth/` call it refreshes the access token once (shared promise) and retries; if that fails it clears the store and redirects to `/login`. Typed wrappers live in `lib/api/*.ts` (analytics, users, integrations, sales, meetings, reports, system, ...). Use `lib/api/errors.ts::apiErrorMessage` to show FastAPI error details. Parse backend timestamps with `lib/dates.ts::parseApiDate` or the helpers in `lib/format.ts`: the API sends naive UTC without an offset, so `new Date()` would read it as local time. Downloads must go through `lib/download.ts` (`downloadFile`), because `window.open` can't send the token.
- Loading/error states: `components/common/ErrorState.tsx` (`ErrorState` with retry, `PageLoading`). Dashboard and Analytics share `components/analytics/AnalyticsFilterBar` and `TrendBadge`.
- Loaders called from effects set state only after their first `await` (spinners for retries are set in the handler), to satisfy `react-hooks/set-state-in-effect` where possible.

### UI conventions (user preferences)

These supersede an earlier redesign brief, which asked for an indigo primary and light mode only. Keep its intent: a calm, professional B2B look with no glow, neon or decorative gradients, and status never conveyed by color alone.

- Every UI element should be a shadcn/ui component. The project uses `components.json` with style `radix-vega`, the unified `radix-ui` package, and `cn` imported from the `cn` package. Prefer `Item`, `Empty`, `Field`, `Spinner`, `InputGroup`, `ToggleGroup`, `AlertDialog` (for destructive confirms) over hand-styled markup. Toasts use `sonner`.
- No emojis anywhere in the UI, including backend mock/AI text that reaches the UI.
- Restyling requests mean "change the look, not the content or behavior."
- Theme: shadcn preset with base `mist`, theme and charts `cyan`, font Inter (`--font-inter`), light/dark/system via `next-themes` (`components/theme-provider.tsx`, `components/mode-toggle.tsx`). Tokens live in `src/app/globals.css`, including custom `--success`, `--warning` and `--brand-panel(-foreground)` tokens.
  - Use `text-success` / `text-warning` / `bg-brand-panel` rather than raw emerald/amber/primary classes so both modes keep ≥4.5:1 text contrast.
  - Charts use shadcn `ChartContainer` with `theme: { light, dark }` colors when a series needs a different shade per mode.
