"""Integration tests for PlayerAvailability (require Postgres; see conftest)."""

import uuid

import pytest

from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def publish(
    client,
    user_id,
    sport="soccer",
    city="Casablanca",
    country="Morocco",
    region=None,
    latitude=33.5731,
    longitude=-7.5898,
    radius_km=10,
):
    return await client.post(
        "/api/v1/player-availability",
        json={
            "sport": sport,
            "city": city,
            "country": country,
            "region": region,
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km,
        },
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
    assert body["city"] == "Casablanca"
    assert body["country"] == "Morocco"


async def test_publish_requires_auth(client):
    resp = await client.post(
        "/api/v1/player-availability",
        json={"sport": "soccer", "city": "Rabat", "latitude": 34.02, "longitude": -6.83, "radius_km": 10},
    )
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


async def test_browse_filters_by_country(client):
    a = await make_user(client, "A", "+15555556100")
    b = await make_user(client, "B", "+15555556101")
    await publish(client, a["id"], city="Casablanca", country="Morocco")
    await publish(client, b["id"], city="Paris", country="France", latitude=48.8566, longitude=2.3522)

    by_country = await client.get("/api/v1/player-availability", params={"country": "France"})
    assert {r["user_id"] for r in by_country.json()} == {b["id"]}


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


async def test_publish_saves_location_to_profile(client):
    user = await make_user(client, "Saver", "+15555556011")
    await publish(client, user["id"], latitude=33.5731, longitude=-7.5898, radius_km=12)

    me = await client.get("/api/v1/users/me", headers=auth_header(user["id"]))
    assert me.json()["latitude"] == 33.5731
    assert me.json()["longitude"] == -7.5898
    assert me.json()["radius_km"] == 12


async def test_publish_falls_back_to_profile_location(client):
    user = await make_user(client, "Reuser", "+15555556012")
    await client.patch(
        "/api/v1/users/me",
        json={"latitude": 34.02, "longitude": -6.83, "radius_km": 20},
        headers=auth_header(user["id"]),
    )

    resp = await client.post(
        "/api/v1/player-availability",
        json={"sport": "soccer", "city": "Rabat"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["latitude"] == 34.02
    assert body["longitude"] == -6.83
    assert body["radius_km"] == 20


async def test_publish_without_location_or_profile_default_fails(client):
    user = await make_user(client, "Blank", "+15555556013")
    resp = await client.post(
        "/api/v1/player-availability",
        json={"sport": "soccer", "city": "Rabat"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 400


async def test_browse_filters_by_player_radius(client):
    # Casablanca center
    near = await make_user(client, "Near", "+15555556008")
    # ~1.5km away, well within a 10km player radius
    await publish(client, near["id"], latitude=33.5731, longitude=-7.5898, radius_km=10)
    # ~9,000km away (New York), well outside any reasonable radius
    far = await make_user(client, "Far", "+15555556009")
    await publish(client, far["id"], latitude=40.7128, longitude=-74.0060, radius_km=10)

    resp = await client.get(
        "/api/v1/player-availability",
        params={"search_lat": 33.5850, "search_lng": -7.6000},
    )
    assert resp.status_code == 200
    ids = {r["user_id"] for r in resp.json()}
    assert near["id"] in ids
    assert far["id"] not in ids


async def test_browse_respects_mutual_search_radius(client):
    owner = await make_user(client, "Owner", "+15555556010")
    # Player's own radius is generous (50km), but the searcher scopes to 1km.
    await publish(client, owner["id"], latitude=33.5731, longitude=-7.5898, radius_km=50)

    # ~9km away from the player's location — outside the searcher's 1km search radius.
    resp = await client.get(
        "/api/v1/player-availability",
        params={"search_lat": 33.65, "search_lng": -7.5898, "search_radius_km": 1},
    )
    assert resp.status_code == 200
    assert owner["id"] not in {r["user_id"] for r in resp.json()}

    resp_wide = await client.get(
        "/api/v1/player-availability",
        params={"search_lat": 33.65, "search_lng": -7.5898, "search_radius_km": 50},
    )
    assert owner["id"] in {r["user_id"] for r in resp_wide.json()}
