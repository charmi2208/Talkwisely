#!/bin/sh
# Prepares the database, then runs the container command (the API or a Celery worker).
#   RUN_MIGRATIONS=false   skip Alembic (set on workers so only the API migrates)
#   SEED_DEMO_DATA=false   don't load the demo organization
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  python -m app.db.migrate

  if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
    echo "Loading demo data (skipped for rows that already exist)..."
    python scripts/seed.py
  fi

  echo "Indexing conversations for search..."
  python scripts/reindex.py || echo "Search indexing skipped; run scripts/reindex.py later."
fi

exec "$@"
