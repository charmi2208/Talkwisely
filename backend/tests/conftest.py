"""
Shared test setup.

Environment variables are set before any test module imports the app, so the whole
run uses a throwaway SQLite database, temp storage and vector store, and mock AI
providers (no network, no API keys), whatever backend/.env.local contains.
"""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="talkwise_test_")
_DB = os.path.join(_TMP, "test.db")

os.environ.update({
    "APP_ENV": "test",
    "APP_DEBUG": "false",
    "DATABASE_URL": f"sqlite+aiosqlite:///{_DB}",
    "DATABASE_SYNC_URL": f"sqlite:///{_DB}",
    "CHROMA_PERSIST_DIR": os.path.join(_TMP, "vectors"),
    "STORAGE_LOCAL_PATH": os.path.join(_TMP, "storage"),
    "LLM_PROVIDER": "mock",
    "STT_PROVIDER": "mock",
    "EMBEDDING_PROVIDER": "mock",
    "TASK_QUEUE": "background",
    "RATE_LIMIT_ENABLED": "false",
    "LOG_LEVEL": "WARNING",
})

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

DEMO_PASSWORDS = {
    "admin@demo.talkwiseai.com": "admin123",
    "manager@demo.talkwiseai.com": "manager123",
    "agent@demo.talkwiseai.com": "agent123",
    "agent2@demo.talkwiseai.com": "agent123",
}


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    """Migrate the temp database and load the demo organization once per run."""
    from scripts.seed import seed_database

    seed_database()
    yield _DB


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=60) as ac:
        yield ac


async def login(client: AsyncClient, email: str, password: str | None = None) -> dict[str, str]:
    """Bearer headers for a user."""
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password or DEMO_PASSWORDS[email]}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def admin(client):
    return await login(client, "admin@demo.talkwiseai.com")


@pytest.fixture
async def manager(client):
    return await login(client, "manager@demo.talkwiseai.com")


@pytest.fixture
async def agent(client):
    return await login(client, "agent@demo.talkwiseai.com")


@pytest.fixture
async def agent2(client):
    return await login(client, "agent2@demo.talkwiseai.com")


# A few bytes are enough: the mock speech-to-text provider ignores the audio
FAKE_AUDIO = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64


async def upload(client: AsyncClient, headers: dict, title: str = "Test sales call") -> str:
    """Upload a recording; returns the conversation id once processing has finished.

    With TASK_QUEUE=background, the pipeline runs as a FastAPI background task, which
    httpx's ASGI transport awaits before returning the response.
    """
    response = await client.post(
        "/api/v1/conversations/upload",
        headers=headers,
        files={"file": ("call.wav", FAKE_AUDIO, "audio/wav")},
        data={"title": title},
    )
    assert response.status_code == 201, response.text
    return response.json()["conversation_id"]
