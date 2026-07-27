"""Coverage for the users router beyond the happy path (require Postgres; see conftest)."""

import uuid

import pytest

from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def test_create_user_duplicate_email(client):
    await client.post(
        "/api/v1/users",
        json={"name": "A", "phone": "+15555551000", "email": "dup@example.com"},
    )
    resp = await client.post(
        "/api/v1/users",
        json={"name": "B", "phone": "+15555551001", "email": "dup@example.com"},
    )
    assert resp.status_code == 409


async def test_update_me_name_and_email(client):
    user = await make_user(client, "Old", "+15555551002")
    resp = await client.patch(
        "/api/v1/users/me",
        json={"name": "New", "email": "new@example.com"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New"
    assert body["email"] == "new@example.com"


async def test_update_me_email_conflict(client):
    taken = await make_user(client, "Taken", "+15555551003")
    await client.patch(
        "/api/v1/users/me",
        json={"email": "taken@example.com"},
        headers=auth_header(taken["id"]),
    )
    other = await make_user(client, "Other", "+15555551004")
    resp = await client.patch(
        "/api/v1/users/me",
        json={"email": "taken@example.com"},
        headers=auth_header(other["id"]),
    )
    assert resp.status_code == 409


async def test_update_me_saves_gender(client):
    user = await make_user(client, "Gendered", "+15555551007")
    resp = await client.patch(
        "/api/v1/users/me",
        json={"gender": "male"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200
    assert resp.json()["gender"] == "male"


async def test_update_me_rejects_invalid_gender(client):
    user = await make_user(client, "Ungendered", "+15555551008")
    resp = await client.patch(
        "/api/v1/users/me",
        json={"gender": "nonbinary"},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 422


async def test_update_me_saves_location(client):
    user = await make_user(client, "Locatable", "+15555551005")
    resp = await client.patch(
        "/api/v1/users/me",
        json={"latitude": 33.5731, "longitude": -7.5898, "radius_km": 15},
        headers=auth_header(user["id"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["latitude"] == 33.5731
    assert body["longitude"] == -7.5898
    assert body["radius_km"] == 15


async def test_unknown_user_id_is_unauthorized(client):
    resp = await client.get("/api/v1/users/me", headers=auth_header(uuid.uuid4()))
    assert resp.status_code == 401


async def test_get_user_404(client):
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_and_list_users(client):
    u1 = await make_user(client, "One", "+15555551005")
    u2 = await make_user(client, "Two", "+15555551006")

    got = await client.get(f"/api/v1/users/{u1['id']}")
    assert got.status_code == 200 and got.json()["id"] == u1["id"]

    listing = await client.get("/api/v1/users")
    ids = {u["id"] for u in listing.json()}
    assert {u1["id"], u2["id"]} <= ids
