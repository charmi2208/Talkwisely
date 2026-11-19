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
| `tests/integration/test_features.py` | Integration | Analytics consistency and filters, manual and overdue action items, auto-action-item preference, sales pipeline and stage changes, meetings, integrations (mock honesty, validation, CRM switch-off, PBX import), saved reports and PDF/CSV/Markdown downloads, CSV export, knowledge base, audit log |
| `tests/integration/test_api_endpoints.py` | Integration | Health and root endpoints |
| `tests/unit/test_pipeline_graph.py` | Unit | LangGraph run order, fan-in, progress, real concurrency, isolated agent failures, failing sequential steps, empty transcripts, graph diagram |
| `tests/unit/test_agent_schemas.py` | Unit | Output validation: repairs, unknown values to null, clamping, defaults, required fields, CRM change shape |
| `tests/unit/test_helpers.py` | Unit | Value coercion, role resolution, rate limiter, preferences, PDF/CSV export, mock routing by task |
| `tests/unit/test_ai_pipeline.py` | Unit | Providers, vector store, Copilot and email agents |
| `tests/unit/test_evaluation_metrics.py` | Unit | Evaluation metrics, dataset shape, mock smoke run |

`tests/run_tests.py` is an older standalone smoke script that needs no pytest; it uses your configured embedding provider.

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
