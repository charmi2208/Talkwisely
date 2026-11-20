# TalkWiseAI API and Celery worker image
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg converts uploads (and extracts audio from video) for hosted Whisper
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 1000 talkwise \
    && mkdir -p storage vector_store \
    && chown -R talkwise:talkwise /app \
    && chmod +x docker-entrypoint.sh
USER talkwise

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
# Hosting platforms (Railway, Render, Fly) pass the port in $PORT
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
