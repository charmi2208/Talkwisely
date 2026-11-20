# Setup guide

Two ways to run TalkWiseAI: directly on your machine (best for development) or with Docker Compose (closest to production).

## Option A: run locally

### Prerequisites

- Python 3.11 or newer (tested with 3.13)
- Node.js 20.9 or newer, with npm
- ffmpeg, only for real transcription: `brew install ffmpeg` (macOS) or `winget install ffmpeg` (Windows)
- A free Groq API key from https://console.groq.com/keys, only for real AI. Without one, the app runs in mock mode.

PostgreSQL and Redis are not needed locally: the app uses SQLite and runs background jobs inside the API process.

### Backend

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt   # Windows: .\venv\Scripts\pip install -r requirements-dev.txt
cp .env.local.example .env.local                 # Windows: Copy-Item .env.local.example .env.local
```

Edit `backend/.env.local` and set `LLM_API_KEY` to your Groq key, or set `LLM_PROVIDER="mock"` and `STT_PROVIDER="mock"` to run without one. `.env.local` is git-ignored; never put real keys in `backend/.env`, which is committed.

```bash
./venv/bin/python start.py                       # Windows: .\venv\Scripts\python start.py
```

`start.py` applies the database migrations, loads the demo organization, indexes conversations for search and starts the API with auto-reload on http://localhost:8000 (interactive docs at http://localhost:8000/api/docs).

The first search downloads the ~80 MB local embedding model to `~/.cache/chroma`.

### Frontend

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
| Agent | agent2@demo.talkwiseai.com | agent123 |

The demo organization has 12 fictional conversations (sales calls, a demo, a negotiation, support escalations, a complaint, a cancellation, a client review and an internal meeting) with full transcripts and insights, spread over the last 60 days, plus two knowledge-base documents. Databases seeded by an older version have placeholder conversations; replace them with:

```bash
./venv/bin/python scripts/seed.py --refresh-demo   # your own uploads are kept
./venv/bin/python scripts/reindex.py
```

Use **Create one** on the login page to start a new, empty workspace instead.

## Option B: Docker Compose

Requires Docker Desktop (or Docker Engine with the Compose plugin).

```bash
docker compose up --build
```

This starts PostgreSQL, the API (which migrates and seeds the database on start) and the web app:

- Web app: http://localhost:3000
- API docs: http://localhost:8000/api/docs

AI providers default to mock. For real AI, create `backend/.env.local` as above; Compose loads it when it exists.

To process recordings on Celery workers instead of inside the API, add the override file. It also starts Redis and a Chroma server, which the API and workers share:

```bash
docker compose -f docker-compose.yml -f docker-compose.celery.yml up --build
```

Data lives in named volumes (`postgres-data`, `backend-storage`, `backend-vectors`, `chroma-data`). `docker compose down -v` deletes them.

## Using real AI

With the Groq values from `.env.local.example`:

| Component | Setting | Notes |
|---|---|---|
| Language model | `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_MODEL=openai/gpt-oss-120b`, `LLM_REASONING_EFFORT=low` | Any OpenAI-compatible API works. Free Groq keys can't use `llama-3.3-70b-versatile`. |
| Speech-to-text | `STT_PROVIDER=whisper_api`, `STT_API_MODEL=whisper-large-v3-turbo` | Reuses the LLM key and base URL unless `STT_API_KEY`/`STT_BASE_URL` are set. Needs ffmpeg. |
| Embeddings | `EMBEDDING_PROVIDER=local` | ONNX all-MiniLM-L6-v2, runs on the CPU, no key. |

After switching embedding provider, rebuild the search index: `./venv/bin/python scripts/reindex.py --all`.

Record the script in `docs/TEST_RECORDING.md` and upload it to see a realistic analysis. A one-minute call takes about 25 seconds with Groq.

## Environment variables

Settings are read from `backend/.env` (committed placeholders), then `backend/.env.local` (git-ignored), then real environment variables; later sources win. Names are case-insensitive.

### Application

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | `development`, `production` or `test`. Production hides internal error details. |
| `APP_DEBUG` | `true` | Logs every SQL statement when true. |
| `APP_SECRET_KEY` | dev placeholder | Change in production. |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8000` | Where `start.py` serves the API. |
| `FRONTEND_URL` | `http://localhost:3000` | Used in password reset links. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated origins allowed to call the API. |
| `CORS_ORIGIN_REGEX` | empty | Extra allowed origins as a regex, e.g. `https://talkwiseai[a-z0-9-]*\.vercel\.app` for Vercel production and preview URLs. |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | Logging verbosity and format (`json` or `text`). |
| `DEMO_MODE_ENABLED` | `true` | Informational; shown in logs. |

### Database and storage

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | PostgreSQL on localhost | Async URL for the API: `sqlite+aiosqlite:///./storage/talkwiseai.db` or `postgresql+asyncpg://user:pass@host/db`. |
| `DATABASE_SYNC_URL` | PostgreSQL on localhost | Sync URL for migrations, seed, reindex and the worker: `sqlite:///...` or `postgresql://...`. Must point at the same database. |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | `10` / `20` | PostgreSQL connection pool. |
| `STORAGE_LOCAL_PATH` | `./storage` | Uploaded recordings and knowledge documents. |
| `STORAGE_MAX_UPLOAD_SIZE_MB` | `500` | Largest accepted upload. |
| `STORAGE_ALLOWED_AUDIO_EXTENSIONS` / `..._VIDEO_EXTENSIONS` | `.mp3,.wav,.m4a,.ogg,.flac` / `.mp4,.avi,.mov,.mkv,.webm` | Accepted upload types. |
| `CHROMA_PERSIST_DIR` | `./vector_store` | Embedded Chroma search index. |
| `CHROMA_HOST` / `CHROMA_PORT` | empty / `8000` | Use a Chroma server instead of the embedded store (required with Celery workers). |

### Authentication and security

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | dev placeholder | Signs access, refresh and password reset tokens. Change in production. |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | The web app refreshes expired access tokens automatically. |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `RATE_LIMIT_ENABLED` | `true` | Per-IP rate limiting. |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_PERIOD_SECONDS` | `300` / `60` | General API limit. Login, register and password reset are limited to 10 per window. |

### AI providers

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `openai` (any OpenAI-compatible API) or `mock` (canned answers). |
| `LLM_API_KEY` | empty | API key for the LLM (and for hosted Whisper unless `STT_API_KEY` is set). |
| `LLM_BASE_URL` | empty | Empty for OpenAI; `https://api.groq.com/openai/v1` for Groq. |
| `LLM_MODEL` | `gpt-4o` | Model name as the API expects it. |
| `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` | `0.1` / `4096` | |
| `LLM_MAX_CONCURRENCY` | `3` | Parallel LLM calls; keeps free-tier rate limits happy. |
| `LLM_REASONING_EFFORT` | empty | `low`/`medium`/`high`, only for reasoning models. Sent only when set. |
| `STT_PROVIDER` | `mock` | `whisper_api` (hosted), `whisper_local` (needs `pip install openai-whisper`) or `mock`. |
| `STT_API_KEY` / `STT_BASE_URL` | empty | Override the LLM key and URL for transcription. |
| `STT_API_MODEL` | `whisper-large-v3-turbo` | Hosted Whisper model. |
| `STT_MAX_UPLOAD_MB` | `25` | Larger files are converted and split into 10-minute parts. |
| `WHISPER_MODEL` | `base` | Model size for `whisper_local`. |
| `EMBEDDING_PROVIDER` | `mock` | `local` (ONNX), `openai` or `mock`. |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | `text-embedding-3-small` / `1536` | For `openai` embeddings. |

### Caching

| Variable | Default | Purpose |
|---|---|---|
| `CACHE_BACKEND` | `memory` | `memory` (per process), `redis` (shared; use with Celery or several API replicas, also moves rate limiting to Redis) or `none`. |
| `CACHE_URL` | empty | Redis URL for the cache; defaults to `REDIS_URL`. |
| `CACHE_TTL_SECONDS` | `60` | Analytics cache lifetime. Writes invalidate earlier. |
| `COPILOT_CACHE_TTL_SECONDS` | `600` | How long identical Copilot questions reuse an answer. |

### Background jobs

| Variable | Default | Purpose |
|---|---|---|
| `TASK_QUEUE` | `background` | `background` runs processing inside the API; `celery` sends it to Celery workers. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis on localhost | Used with `TASK_QUEUE=celery`. |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `PBX_AUTO_SYNC_INTERVAL_MINUTES` | `15` | How often the PBX auto-sync runs for users who turned it on. |

### Integrations

Only mock adapters are implemented; these variables are reserved for real adapters (see `docs/INTEGRATIONS.md`). Which provider each organization uses, and its non-secret settings, are configured on the Integrations page and stored in the database.

| Variable | Purpose |
|---|---|
| `CRM_PROVIDER`, `HUBSPOT_API_KEY`, `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET` | CRM adapter credentials |
| `CALENDAR_PROVIDER`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Calendar adapter credentials |
| `EMAIL_PROVIDER`, `SENDGRID_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` | Email adapter credentials. With the mock provider in development, password reset links are returned by the API instead of emailed. |
| `TALKWISELY_PROVIDER`, `TALKWISELY_API_BASE_URL`, `TALKWISELY_API_KEY`, `TALKWISELY_ACCOUNT_ID` | TalkWisely PBX adapter credentials |
| `STORAGE_PROVIDER`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET` | Reserved for object storage (only `local` is implemented) |

### Frontend

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | API base URL used by the browser. Compiled into the build, so rebuild after changing it. |
