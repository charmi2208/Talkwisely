#!/usr/bin/env python3
"""
TalkWiseAI Backend Development Server Startup Script.

Runs:
1. Database table creation
2. Database seed (demo data)
3. FastAPI server with hot reload

Prerequisites:
- PostgreSQL running with database 'talkwiseai'
- Redis running
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

    # Step 1: Create database tables
    print("📦 Creating database tables...")
    try:
        from sqlalchemy import create_engine
        from app.core.config import settings
        from app.db.session import Base

        # Import all models to ensure they're registered
        import app.db.models  # noqa

        engine = create_engine(settings.database_sync_url)
        Base.metadata.create_all(engine)
        engine.dispose()
        print("   ✅ Database tables ready\n")
    except Exception as e:
        print(f"   ⚠️  Database setup failed: {e}")
        print("   Make sure PostgreSQL is running and the database exists.")
        print("   Create with: createdb talkwiseai\n")

    # Step 2: Run seed
    print("🌱 Seeding demo data...")
    try:
        from scripts.seed import seed_database
        seed_database()
    except Exception as e:
        print(f"   ⚠️  Seed failed (may already be seeded): {e}\n")

    # Step 3: Start server
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
        "--log-level", "info",
    ], cwd=backend_dir)


if __name__ == "__main__":
    main()
