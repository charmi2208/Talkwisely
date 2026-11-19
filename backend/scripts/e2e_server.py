"""
Start a throwaway API for the browser end-to-end tests (frontend/e2e).

Creates a temporary SQLite database with the demo organization, uses mock AI providers
and temporary storage, turns rate limiting off, and serves on the given port. Nothing
touches your real database, uploads or search index.

    ./venv/bin/python scripts/e2e_server.py --port 8020 --web-origin http://localhost:3020
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--web-origin", default="http://localhost:3020")
    args = parser.parse_args()

    tmp = tempfile.mkdtemp(prefix="talkwise_e2e_")
    db = os.path.join(tmp, "e2e.db")
    os.environ.update({
        "APP_ENV": "development",
        "APP_DEBUG": "false",
        "LOG_LEVEL": "WARNING",
        "DATABASE_URL": f"sqlite+aiosqlite:///{db}",
        "DATABASE_SYNC_URL": f"sqlite:///{db}",
        "STORAGE_LOCAL_PATH": os.path.join(tmp, "storage"),
        "CHROMA_PERSIST_DIR": os.path.join(tmp, "vectors"),
        "LLM_PROVIDER": "mock",
        "STT_PROVIDER": "mock",
        "EMBEDDING_PROVIDER": "mock",
        "TASK_QUEUE": "background",
        "CACHE_BACKEND": "memory",
        "RATE_LIMIT_ENABLED": "false",
        "CORS_ORIGINS": args.web_origin,
        "FRONTEND_URL": args.web_origin,
    })
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))

    from scripts.seed import seed_database

    seed_database()

    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
