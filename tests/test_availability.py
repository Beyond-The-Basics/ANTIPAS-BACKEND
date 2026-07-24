"""Integration tests for PlayerAvailability (require Postgres; see conftest)."""

import uuid

import pytest

from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def publish(client, user_id, sport="soccer", city="Casablanca"):
    return await client.post(
        "/api/v1/player-availability",
        json={"sport": sport, "city": city},
        headers=auth_header(user_id),
    )


async def test_publish_sets_owner_and_open(client):
    user = await make_user(client, "Solo", "+15555556000")
    resp = await publish(client, user["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user_id"] == user["id"]
    assert body["status"] == "open"
    assert body["sport"] == "soccer"


async def test_publish_requires_auth(client):
    resp = await client.post("/api/v1/player-availability", json={"sport": "soccer", "city": "Rabat"})
    assert resp.status_code == 401  # no bearer token and no stub header


async def test_browse_filters_by_sport_and_city(client):
    a = await make_user(client, "A", "+15555556001")
    b = await make_user(client, "B", "+15555556002")
    await publish(client, a["id"], sport="soccer", city="Casablanca")
    await publish(client, b["id"], sport="tennis", city="Rabat")

    by_sport = await client.get("/api/v1/player-availability", params={"sport": "tennis"})
    assert {r["user_id"] for r in by_sport.json()} == {b["id"]}

    by_city = await client.get("/api/v1/player-availability", params={"city": "Casablanca"})
    assert {r["user_id"] for r in by_city.json()} == {a["id"]}


async def test_withdraw_owner_only(client):
    owner = await make_user(client, "Owner", "+15555556003")
    other = await make_user(client, "Other", "+15555556004")
    listing = (await publish(client, owner["id"])).json()

    denied = await client.post(
        f"/api/v1/player-availability/{listing['id']}/withdraw",
        headers=auth_header(other["id"]),
    )
    assert denied.status_code == 403

    ok = await client.post(
        f"/api/v1/player-availability/{listing['id']}/withdraw",
        headers=auth_header(owner["id"]),
    )
    assert ok.status_code == 204

    # withdrawn listings drop out of browse
    listed = await client.get("/api/v1/player-availability")
    assert listing["id"] not in {r["id"] for r in listed.json()}


async def test_cannot_withdraw_twice(client):
    owner = await make_user(client, "Owner", "+15555556005")
    listing = (await publish(client, owner["id"])).json()
    first = await client.post(
        f"/api/v1/player-availability/{listing['id']}/withdraw",
        headers=auth_header(owner["id"]),
    )
    assert first.status_code == 204
    second = await client.post(
        f"/api/v1/player-availability/{listing['id']}/withdraw",
        headers=auth_header(owner["id"]),
    )
    assert second.status_code == 400


async def test_list_mine(client):
    owner = await make_user(client, "Owner", "+15555556006")
    other = await make_user(client, "Other", "+15555556007")
    await publish(client, owner["id"], city="Casablanca")
    await publish(client, owner["id"], sport="tennis", city="Rabat")
    await publish(client, other["id"])

    mine = await client.get("/api/v1/users/me/availability", headers=auth_header(owner["id"]))
    assert mine.status_code == 200
    assert len(mine.json()) == 2
    assert all(r["user_id"] == owner["id"] for r in mine.json())


async def test_get_availability_404(client):
    resp = await client.get(f"/api/v1/player-availability/{uuid.uuid4()}")
    assert resp.status_code == 404
