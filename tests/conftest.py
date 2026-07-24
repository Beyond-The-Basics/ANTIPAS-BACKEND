"""Test fixtures.

Integration tests need Postgres (the models use Postgres-specific types: UUID, ARRAY). They run
against a dedicated `antipas_test` database and create/drop the schema per test. If Postgres isn't
reachable, these fixtures skip rather than fail, so `pytest` stays green without infra.
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.models.game_type import GameType

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


async def a_game_type(db_session, sport: str = "soccer") -> GameType:
    """Fetch a GameType for `sport`, creating a minimal one if the (per-test, empty) DB has none."""
    gt = await db_session.scalar(select(GameType).where(GameType.sport == sport))
    if gt is None:
        by_sport = {"soccer": ("5v5", 5), "tennis": ("singles", 1), "paddle": ("doubles", 2)}
        label, players_per_side = by_sport[sport]
        gt = GameType(sport=sport, label=label, players_per_side=players_per_side)
        db_session.add(gt)
        await db_session.commit()
        await db_session.refresh(gt)
    return gt


async def completed_team(client, db_session, captain: dict, name: str, sport: str = "soccer") -> dict:
    """A team with a lineup type set and just enough active members to be marked completed."""
    team = await make_team(client, captain["id"], name=name, sport=sport)
    game_type = await a_game_type(db_session, sport)
    for i in range(game_type.players_per_side - 1):  # captain is already one of them
        member = await make_user(client, f"{name} P{i}", f"+1{uuid.uuid4().int % 10**11:011d}")
        await add_member(db_session, team["id"], member["id"], role="member")
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(game_type.id), "completed": True},
        headers=auth_header(captain["id"]),
    )
    assert resp.status_code == 200 and resp.json()["completed"] is True, resp.text
    return resp.json()
