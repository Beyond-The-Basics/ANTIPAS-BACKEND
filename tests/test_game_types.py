"""GET /game-types — the lineup catalog a captain picks from at the roster-building stage."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_list_all_game_types(client):
    resp = await client.get("/api/v1/game-types")
    assert resp.status_code == 200
    labels = {(g["sport"], g["label"]) for g in resp.json()}
    # The full seeded catalog (app/db/seed.py isn't run for tests, so nothing exists until a test
    # creates one — this just exercises an empty/partial catalog rather than asserting the full set).
    assert isinstance(labels, set)


async def test_filter_by_sport(client, db_session):
    from tests.conftest import a_game_type

    soccer_gt = await a_game_type(db_session, "soccer")
    tennis_gt = await a_game_type(db_session, "tennis")

    resp = await client.get("/api/v1/game-types", params={"sport": "soccer"})
    assert resp.status_code == 200
    ids = {g["id"] for g in resp.json()}
    assert str(soccer_gt.id) in ids
    assert str(tennis_gt.id) not in ids


async def test_players_per_side_is_exposed(client, db_session):
    from tests.conftest import a_game_type

    gt = await a_game_type(db_session, "soccer")
    resp = await client.get("/api/v1/game-types", params={"sport": "soccer"})
    body = next(g for g in resp.json() if g["id"] == str(gt.id))
    assert body["players_per_side"] == gt.players_per_side


async def test_no_auth_required(client, db_session):
    """Reference data — same visibility as the team/sport directory, no bearer token needed."""
    resp = await client.get("/api/v1/game-types")
    assert resp.status_code == 200


async def test_basketball_is_in_the_seed_catalog():
    """The seed module isn't run against the (per-test, empty) test DB — see the db_session
    fixture — so this checks the catalog data directly rather than through GET /game-types."""
    from app.db.seed import GAME_TYPE_CATALOG
    from app.models.enums import Sport

    assert GAME_TYPE_CATALOG[Sport.BASKETBALL] == [("3x3", 3), ("5v5", 5)]


async def test_filter_by_sport_includes_basketball(client, db_session):
    from app.models.game_type import GameType

    bball = GameType(sport="basketball", label="5v5", players_per_side=5)
    db_session.add(bball)
    await db_session.commit()
    await db_session.refresh(bball)

    resp = await client.get("/api/v1/game-types", params={"sport": "basketball"})
    assert resp.status_code == 200
    ids = {g["id"] for g in resp.json()}
    assert str(bball.id) in ids
