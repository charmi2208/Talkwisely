# Testing guide

## Backend tests

```bash
cd backend
./venv/bin/pip install -r requirements-dev.txt   # once
./venv/bin/pytest                                 # whole suite (about a minute)
./venv/bin/pytest tests/e2e -v                    # just the end-to-end workflow
./venv/bin/pytest --cov=app --cov-report=term-missing
```

The suite never touches your real data or calls external services. `tests/conftest.py` sets environment variables before the app is imported:

- a throwaway SQLite database, migrated with Alembic and loaded with the demo organization once per run
- temporary file storage and vector store
- mock LLM, speech-to-text and embedding providers, whatever `backend/.env.local` says
- rate limiting off (one test turns it on deliberately)

API tests call the app in-process through `httpx.ASGITransport`. Uploads run the real background job, which the transport awaits, so a test can read the analysis right after uploading.

### What is covered

| File | Kind | Covers |
|---|---|---|
| `tests/e2e/test_full_workflow.py` | End to end | Spec §61 workflow: log in, upload, transcription, AI analysis, every insight type, speaker renaming, follow-up task, email draft, CRM approval, Copilot, notifications, reprocessing, deletion; rejected file types |
| `tests/integration/test_auth_and_users.py` | Integration | Register, login, profile, change password, password reset (single use), login rate limit, team management, self-lockout guards, preferences |
| `tests/integration/test_rbac.py` | Integration | Agents blocked from admin endpoints; managers can view but not manage; agents see only their own conversations, insights, Copilot context and leaderboard row |
| `tests/integration/test_features.py` | Integration | Analytics consistency, filters and cache invalidation, meeting import, manual and overdue action items, auto-action-item preference, sales pipeline and stage changes, meetings, integrations (mock honesty, validation, CRM switch-off, PBX import), saved reports and PDF/CSV/Markdown downloads, CSV export, knowledge base, audit log |
| `tests/integration/test_api_endpoints.py` | Integration | Health and root endpoints |
| `tests/unit/test_pipeline_graph.py` | Unit | LangGraph run order, fan-in, progress, real concurrency, isolated agent failures, failing sequential steps, empty transcripts, graph diagram |
| `tests/unit/test_agent_schemas.py` | Unit | Output validation: repairs, unknown values to null, clamping, defaults, required fields, CRM change shape |
| `tests/unit/test_helpers.py` | Unit | Value coercion, role resolution, rate limiter, preferences, PDF/CSV export, mock routing by task |
| `tests/unit/test_ai_pipeline.py` | Unit | Providers, vector store, Copilot and email agents |
| `tests/unit/test_evaluation_metrics.py` | Unit | Evaluation metrics, dataset shape, mock smoke run |
| `tests/unit/test_nl_analytics_routing.py` | Unit | Question routing, period parsing, validated LLM routing |
| `tests/unit/test_cache.py` | Unit | Memory and Redis caches (fakeredis), generation invalidation on commit, Redis rate limiter |
| `tests/integration/test_nl_analytics.py` | Integration | The spec's analytics questions through the Copilot, numbers matching the analytics API, agent scoping, fallback to search |

`tests/run_tests.py` is an older standalone smoke script that needs no pytest; it uses your configured embedding provider.

## Browser end-to-end tests

Playwright drives Google Chrome through the real web app and API:

```bash
cd frontend
npm run test:e2e
```

`playwright.config.ts` starts a throwaway API (`backend/scripts/e2e_server.py`: temporary SQLite database with the demo organization, mock AI, rate limiting off) on port 8020, then builds the web app and serves the production build on port 3020. A run takes about a minute plus the build. It needs `backend/venv` and Google Chrome. Stop any `next dev` for the project first, since the build writes the same `.next` folder.

| File | Covers |
|---|---|
| `e2e/auth.spec.ts` | Sign in, live dashboard, staying signed in after a reload, sign out, wrong-password error, redirect for signed-out visitors |
| `e2e/roles.spec.ts` | Agents don't see Team or the team filter; admins add a member |
| `e2e/workflow.spec.ts` | Spec §61 through the UI: upload, wait for analysis, insights, rename speakers, follow-up email draft, approve the CRM proposal |
| `e2e/features.spec.ts` | Analytics question in the Copilot, add and complete a task, saved preferences, meeting recordings import |

## Frontend checks

```bash
cd frontend
npx tsc --noEmit     # type check
npm run lint         # ESLint (some older files still have warnings)
npm run build        # production build
```

## AI evaluation

Accuracy of the agents with a real model is measured separately because it needs an API key and takes a few minutes: see `backend/evaluation/README.md`.

## Manual test with real audio

Record the script in `docs/TEST_RECORDING.md`, upload it with real providers configured, and compare the results with the expected analysis listed there.
