# Deployment guide

TalkWiseAI is cloud-agnostic: a Next.js app, a FastAPI service, PostgreSQL, file storage, and optionally Redis, Celery workers and a Chroma server.

## Recommended topology

| Part | Suggested service | Notes |
|---|---|---|
| Web app | Vercel, Netlify, or any Node.js host (`frontend/Dockerfile`) | Build with `NEXT_PUBLIC_API_URL` set to the public API URL; it's compiled into the bundle. |
| API | Any container host (`backend/Dockerfile`) | One or more replicas behind HTTPS. The entrypoint runs migrations and, unless disabled, loads demo data. |
| Database | Managed PostgreSQL 14+ | Set both `DATABASE_URL` (`postgresql+asyncpg://...`) and `DATABASE_SYNC_URL` (`postgresql://...`). |
| Background jobs | Celery workers on the same image | Needed when running more than one API replica. Command: `celery -A app.workers.celery_app worker --loglevel=info`. |
| Broker | Managed Redis | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`. |
| Vector store | Chroma server (`chromadb/chroma`, same version as the client) | Set `CHROMA_HOST`/`CHROMA_PORT`. The embedded store only works for a single process. |
| Files | Persistent volume mounted at `STORAGE_LOCAL_PATH` | Shared by the API and workers. Object storage (S3) is reserved in settings but not implemented. |

A single small server can run the default Docker Compose stack (API with in-process jobs, embedded Chroma, PostgreSQL) for demos and pilots.

## Current live deployment (Railway + Vercel)

| Part | Where | Address |
|---|---|---|
| Web app | Vercel project `talkwiseai` (charmi-dodiyas-projects) | https://talkwiseai-app.vercel.app |
| API | Railway project `talkwiseai`, service `backend` (built from `backend/Dockerfile`) | https://backend-production-7416ad7c.up.railway.app (docs at `/api/docs`) |
| Database | Railway PostgreSQL, referenced as `DATABASE_URL=${{Postgres.DATABASE_URL}}` | private network only |
| Files and search index | Railway volume mounted at `/app/data` (`STORAGE_LOCAL_PATH=/app/data/storage`, `CHROMA_PERSIST_DIR=/app/data/vectors`) | |

How it was set up (Railway CLI 5.x, Vercel CLI):

```bash
# Backend (from backend/)
railway login
railway init --name talkwiseai
railway add --database postgres
railway add --service backend && railway service link backend
railway volume add --mount-path /app/data
railway variables --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --set 'DATABASE_SYNC_URL=${{Postgres.DATABASE_URL}}' \
  --set APP_ENV=production --set RAILWAY_RUN_UID=0 ...          # see docs/SETUP.md for the full list
printf '%s' "$GROQ_KEY" | railway variables --set-from-stdin LLM_API_KEY   # secrets via stdin
railway domain
railway up --detach

# Frontend (from frontend/)
vercel project add talkwiseai && vercel link --project talkwiseai
vercel env add NEXT_PUBLIC_API_URL production   # https://<backend domain>/api/v1
vercel deploy --prod
```

Notes:
- `RAILWAY_RUN_UID=0` lets the container write to the volume (Railway mounts volumes as root; the image otherwise runs as an unprivileged user).
- The app accepts the plain `postgresql://` URL Railway provides and derives the asyncpg URL itself.
- CORS allows the Vercel domains through `CORS_ORIGIN_REGEX=https://talkwiseai[a-z0-9-]*\.vercel\.app`; `FRONTEND_URL` is the web app address used in password reset links.
- `.railwayignore` keeps `.env.local`, the virtualenv and local data out of uploads.
- **Redeploy the API:** `cd backend && railway up --detach`. Variables change with `railway variables --set KEY=value` (this redeploys).
- **Redeploy the web app:** `cd frontend && vercel deploy --prod`. On the Vercel Hobby plan, deployments whose latest git commit was authored by someone outside the Vercel account are blocked ("the commit author doesn't have permission"). Either deploy from a copy of `frontend/` outside the git repository (the CLI then sends no git metadata), or have the account owner make the commit.
- Vercel Authentication (deployment protection) is on by default and covers `*.vercel.app` addresses, so visitors are asked to log in to Vercel until it's turned off under Project Settings → Deployment Protection.
- The demo logins are seeded on the live site. Anyone with the link can use them, including the real AI features, which use the configured Groq key.

## Docker Compose

```bash
docker compose up --build -d                                                    # API + web + PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.celery.yml up --build -d # adds Redis, Chroma, workers
docker compose logs -f backend
```

Before exposing it publicly, change the values below in `backend/.env.local` or the environment. The defaults in the compose file are for local use.

## Production checklist

- [ ] `APP_ENV=production` (hides internal error details) and `APP_DEBUG=false`
- [ ] Strong random `JWT_SECRET_KEY` and `APP_SECRET_KEY` (for example `openssl rand -hex 32`)
- [ ] Database password changed from `talkwise`; database not reachable from the internet
- [ ] `CORS_ORIGINS` and `FRONTEND_URL` set to the real web app URL
- [ ] HTTPS in front of both the API and the web app
- [ ] `SEED_DEMO_DATA=false` on the API container after the first deploy (or from the start)
- [ ] Real AI configured (`LLM_PROVIDER`, `LLM_API_KEY`, `STT_PROVIDER`, `EMBEDDING_PROVIDER`), and ffmpeg available (it is in the image)
- [ ] With more than one API replica: `TASK_QUEUE=celery`, Redis, a Chroma server, and a rate-limit store shared across replicas (the built-in limiter is per process; see `core/rate_limit.py`)
- [ ] Backups for PostgreSQL, the storage volume and the Chroma data
- [ ] A real email adapter before relying on password reset emails (with the mock, links are only returned to the browser in development)

## Upgrades

Database changes ship as Alembic migrations in `backend/alembic/versions`. The API container applies them on start (`RUN_MIGRATIONS=true`); workers set `RUN_MIGRATIONS=false` so only one process migrates. To migrate manually:

```bash
python -m app.db.migrate
```

After changing the embedding provider, rebuild the search index: `python scripts/reindex.py --all`.

## Health checks

`GET /health` returns service status and the active providers; the compose file uses it. The web app has no special endpoint; check that `/login` responds.
