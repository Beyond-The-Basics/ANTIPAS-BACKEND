"""Test fixtures.

Integration tests need Postgres (the models use Postgres-specific types: UUID, ARRAY). They run
against a dedicated `antipas_test` database and create/drop the schema per test. If Postgres isn't
reachable, these fixtures skip rather than fail, so `pytest` stays green without infra.
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://antipas:antipas@localhost:5432/antipas_test",
)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # DB not reachable / test DB missing
        await engine.dispose()
        pytest.skip(f"Postgres test DB unavailable: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """AsyncClient whose get_db yields the test session. Auth is the stub: pass X-User-Id."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def auth_header(user_id) -> dict[str, str]:
    """Stub-auth header. Becomes a Bearer token once Firebase auth is swapped in."""
    return {"X-User-Id": str(user_id)}


# --- shared builders used across test modules ---------------------------------


async def make_user(client, name: str, phone: str) -> dict:
    resp = await client.post("/api/v1/users", json={"name": name, "phone": phone})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def make_team(client, captain_id: str, name: str = "Falcons", sport: str = "soccer") -> dict:
    resp = await client.post(
        "/api/v1/teams",
        json={"name": name, "sport": sport},
        headers=auth_header(captain_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def add_member(db_session, team_id: str, user_id: str, role: str = "member") -> None:
    """Insert an active membership directly (the invite/accept flow is a later milestone)."""
    from app.models.enums import MembershipStatus, TeamRole
    from app.models.team import TeamMembership

    db_session.add(
        TeamMembership(
            team_id=team_id,
            user_id=user_id,
            role=TeamRole(role),
            status=MembershipStatus.ACTIVE,
        )
    )
    await db_session.commit()
