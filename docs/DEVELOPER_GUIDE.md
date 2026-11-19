# Developer guide

How the code is organized and how to extend it. Setup is in `docs/SETUP.md`; `CLAUDE.md` has more detailed notes on architecture and conventions.

## Repository layout

```
backend/
  app/
    api/v1/          one router per area; each sets its own prefix
    ai/
      pipeline/      LangGraph graph, nodes (agents), state
      schemas/       structured output schemas for each agent
      agents/        Copilot, follow-up email and report agents
      providers/     LLM, speech-to-text, embedding providers (real and mock)
      rag/           vector store and indexer
    core/            settings, security, access rules, preferences, rate limiting, logging
    db/              models, session, migration helper, AI-output sanitizer
    integrations/    adapter interfaces, mocks, registry
    services/        PBX import, scheduler, report export
    workers/         background processing job (in-process or Celery)
  alembic/           migrations
  evaluation/        AI evaluation dataset, runner and results
  scripts/           seed, reindex, generate_docs
  tests/             unit, integration, e2e
frontend/src/
  app/(auth)/        login, register, forgot and reset password
  app/(dashboard)/   app pages; layout.tsx guards them
  components/        ui/ (shadcn), layout/, conversation/, analytics/, common/
  lib/               API modules, auth store, formatting and download helpers
```

## Backend conventions

- **Scope every query.** Use `conversation_scope(current_user)` (`core/access.py`) for anything tied to conversations, so agents only see their own and everything stays inside the organization. For other organization-owned rows, filter by `organization_id`.
- **Check roles with dependencies.** `Depends(require_roles("admin"))` or `require_roles("admin", "manager")`. `get_current_user` loads roles eagerly, so `primary_role(user)` and `is_privileged(user)` never query.
- **Audit important actions.** Add an `AuditLog` row for anything a reviewer would want to trace (approvals, deletions, settings changes).
- **No fake success.** If something can't be done (an adapter isn't implemented, a feature is off), return a clear 4xx with a message the UI can show.
- **Schema changes need a migration.** Edit `db/models/models.py`, then from `backend/`:
  ```bash
  ./venv/bin/alembic revision --autogenerate -m "describe the change"
  ```
  Review the generated file (name constraints explicitly; SQLite uses batch mode), run `./venv/bin/python -m app.db.migrate`, then `./venv/bin/alembic check` should report no differences. Regenerate the reference docs with `./venv/bin/python scripts/generate_docs.py`.
- **Close HTTP providers in the loop that created them**: `async with llm_session() as llm` in routes; the worker closes its providers before `asyncio.run` ends.

## Adding a pipeline agent

1. Write the node in `ai/pipeline/nodes.py`: `async def node_x(state, llm) -> dict`. Build the prompt, call `_safe_call_agent(llm, system, user, "x")`, return only the new fields plus `"steps_completed": ["x"]`. Never touch the database.
2. Add the output fields to `ConversationState` (`state.py`). If several parallel nodes write the same field, give it a reducer.
3. Add a schema class to `ai/schemas/agent_outputs.py` and register it in `SCHEMAS` under the task name `"x"`.
4. Add the node to the graph in `graph.py`: into `ANALYSIS_NODES` to run in parallel, or `POST_ANALYSIS_STEPS` to run after the fan-in.
5. Add a canned response to `MockLLMProvider._TASK_GENERATORS` so mock mode and the tests exercise it; it must pass its own schema (`tests/unit/test_agent_schemas.py` checks this).
6. Store the results in `workers/conversation_tasks.py` (new model and migration if needed) and expose them in `GET /conversations/{id}/insights`.
7. If it's measurable, add expected labels to `evaluation/dataset.json` and a metric to `evaluation/run_eval.py`.

## Adding an endpoint

1. Add it to the right router in `app/api/v1/` with Pydantic request and response models and a one-line docstring (it becomes the API reference description).
2. Apply scoping and role checks as above.
3. Add an integration test in `tests/integration/`.
4. Add a typed wrapper in `frontend/src/lib/api/` and use it from the page.
5. Run `./venv/bin/python scripts/generate_docs.py` to refresh `docs/API.md`.

## Frontend conventions

- Every page is a client component wrapped in `AppShell`. Data comes from the typed modules in `lib/api/`; show `PageLoading` while loading and `ErrorState` (with retry) on failure. Never fall back to sample data.
- Use shadcn/ui components for everything (`npx shadcn@latest add <component>`); no emojis in the UI.
- Use the theme tokens (`text-success`, `text-warning`, `bg-brand-panel`) rather than raw colors, and never convey status by color alone.
- Show and hide actions with `useRole()`, but rely on the API for enforcement.
- Parse API timestamps with `parseApiDate` / the helpers in `lib/format.ts`; download files through `lib/download.ts` so the bearer token is sent.
- Show API error details with `apiErrorMessage(err, fallback)`.

## Before opening a pull request

```bash
cd backend && ./venv/bin/pytest
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```
