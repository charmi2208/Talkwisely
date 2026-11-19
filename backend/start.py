#!/usr/bin/env python3
"""
TalkWiseAI Backend Development Server Startup Script.

Runs:
1. Alembic migrations (creates or upgrades the schema)
2. Database seed (demo data)
3. Search index backfill
4. FastAPI server with hot reload

Prerequisites:
- The database in DATABASE_SYNC_URL (SQLite works out of the box; PostgreSQL must be running)
- Redis only if TASK_QUEUE=celery
- Python virtual environment activated
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting TalkWiseAI Backend...\n")

    # Add backend directory to Python path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, backend_dir)

    # Step 1: Create or upgrade the schema with Alembic migrations
    print("📦 Migrating database schema...")
    try:
        from app.db.migrate import upgrade_database

        upgrade_database()
        print("   ✅ Database schema up to date\n")
    except Exception as e:
        print(f"   ⚠️  Database migration failed: {e}")
        print("   Check DATABASE_SYNC_URL, and that PostgreSQL is running if you use it.\n")

    # Step 2: Run seed
    print("🌱 Seeding demo data...")
    try:
        from scripts.seed import seed_database
        seed_database()
    except Exception as e:
        print(f"   ⚠️  Seed failed (may already be seeded): {e}\n")

    # Step 3: Build the semantic search index for anything not indexed yet
    print("🔎 Updating search index...")
    try:
        import asyncio
        from scripts.reindex import reindex
        asyncio.run(reindex())
    except Exception as e:
        print(f"   ⚠️  Search indexing skipped: {e}\n")

    # Step 4: Start server
    print("\n🌐 Starting FastAPI server...")
    print("   API:  http://localhost:8000")
    print("   Docs: http://localhost:8000/api/docs")
    print("   Press CTRL+C to stop\n")

    from app.core.config import settings
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", settings.app_host,
        "--port", str(settings.app_port),
        "--reload",
        "--reload-dir", "app",  # don't watch venv/ or storage/
        "--log-level", "info",
    ], cwd=backend_dir)


if __name__ == "__main__":
    main()
