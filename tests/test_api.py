from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import create_app
from app.services.checker import ProbeResult


@pytest_asyncio.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def fake_probe(url: str, expected_status: int = 200) -> ProbeResult:
        return ProbeResult(
            is_up=True,
            status_code=expected_status,
            response_time_ms=42.5,
            error_message=None,
        )

    monkeypatch.setattr("app.services.monitors.probe_url", fake_probe)

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()
    await engine.dispose()


async def _register_and_login(client: AsyncClient) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "demo@pulsecheck.dev",
            "full_name": "Demo User",
            "password": "secret123",
        },
    )
    assert register.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "demo@pulsecheck.dev", "password": "secret123"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "PulseCheck"


@pytest.mark.asyncio
async def test_register_login_and_me(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "demo@pulsecheck.dev"


@pytest.mark.asyncio
async def test_monitor_lifecycle(client: AsyncClient) -> None:
    token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/monitors",
        headers=headers,
        json={
            "name": "Example",
            "url": "https://example.com",
            "interval_seconds": 60,
            "expected_status": 200,
        },
    )
    assert created.status_code == 201
    monitor_id = created.json()["id"]

    checked = await client.post(f"/api/v1/monitors/{monitor_id}/check", headers=headers)
    assert checked.status_code == 200
    assert checked.json()["is_up"] is True
    assert checked.json()["response_time_ms"] == 42.5

    stats = await client.get(f"/api/v1/monitors/{monitor_id}/stats", headers=headers)
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_checks"] == 1
    assert body["uptime_percentage"] == 100.0
    assert body["last_status"] == "up"

    deleted = await client.delete(f"/api/v1/monitors/{monitor_id}", headers=headers)
    assert deleted.status_code == 204
