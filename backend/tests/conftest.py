import os
import sys
import tempfile

# Point the app at a throwaway SQLite database BEFORE app modules import
# (the engine is created at import time in app.database.session).
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="nexus_test_"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.database.session import async_session_factory, engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    import asyncio

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_setup())
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def register_user(client: TestClient, email: str, password: str = "password123", name: str = "Test User") -> dict:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )
    assert res.status_code == 201, res.text
    return res.json()


def auth_headers(client: TestClient, email: str, password: str = "password123") -> dict:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def run_async(coro):
    import asyncio

    return asyncio.run(coro)
