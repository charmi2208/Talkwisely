"""
Celery application configuration for TalkWiseAI background tasks.

Workers handle long-running operations:
- Audio/video processing
- Transcription (Whisper)
- AI pipeline (LangGraph)
- Embedding generation
- Report generation
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "talkwiseai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.conversation_tasks",
        "app.workers.embedding_tasks",
        "app.workers.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                    # Ack only after task completes
    worker_prefetch_multiplier=1,            # Process one task at a time per worker
    task_routes={
        "app.workers.conversation_tasks.*": {"queue": "conversations"},
        "app.workers.embedding_tasks.*": {"queue": "embeddings"},
        "app.workers.report_tasks.*": {"queue": "reports"},
    },
    task_time_limit=3600,                   # Hard limit: 1 hour
    task_soft_time_limit=3300,              # Soft limit: 55 minutes
)
