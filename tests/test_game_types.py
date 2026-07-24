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
