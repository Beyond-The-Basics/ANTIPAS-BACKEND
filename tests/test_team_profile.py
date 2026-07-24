"""Team profile fields (description/country/city) and the name-search used to invite by name."""

import pytest

from tests.conftest import auth_header, make_team, make_user

pytestmark = pytest.mark.asyncio


async def test_create_team_defaults_country_when_omitted(client):
    cap = await make_user(client, "Cap", "+15555553000")
    team = await make_team(client, cap["id"])
    assert team["country"] == "Morocco"
    assert team["city"] is None
    assert team["description"] is None


async def test_create_team_with_full_profile(client):
    cap = await make_user(client, "Cap", "+15555553001")
    resp = await client.post(
        "/api/v1/teams",
        json={
            "name": "Casablanca Kickers",
            "sport": "soccer",
            "description": "5-a-side, weekend league",
            "country": "Morocco",
            "city": "Casablanca",
            "logo_url": "https://example.com/logo.png",
        },
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["description"] == "5-a-side, weekend league"
    assert body["city"] == "Casablanca"
    assert body["logo_url"] == "https://example.com/logo.png"


async def test_update_team_profile_fields(client):
    cap = await make_user(client, "Cap", "+15555553002")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"description": "Now recruiting", "country": "Spain", "city": "Madrid"},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["description"] == "Now recruiting"
    assert body["country"] == "Spain"
    assert body["city"] == "Madrid"
    # untouched fields survive a partial update
    assert body["name"] == team["name"]


async def test_update_team_profile_requires_captain_or_admin(client):
    cap = await make_user(client, "Cap", "+15555553003")
    outsider = await make_user(client, "Out", "+15555553004")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"city": "Hijacked"},
        headers=auth_header(outsider["id"]),
    )
    assert resp.status_code == 403


@pytest.mark.parametrize(
    "field,value",
    [
        ("description", "x" * 501),  # over MAX_DESCRIPTION_LENGTH
        ("country", ""),  # below min_length
        ("city", ""),
    ],
)
async def test_team_profile_validates_input(client, field, value):
    cap = await make_user(client, "Cap", "+15555553005")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}", json={field: value}, headers=auth_header(cap["id"])
    )
    assert resp.status_code == 422, resp.text


# --- name search (invite-by-name) ---------------------------------------------


async def test_list_users_search_by_name_substring_case_insensitive(client):
    await make_user(client, "Zinedine Zidane", "+15555553006")
    await make_user(client, "Karim Benzema", "+15555553007")
    await make_user(client, "N'Golo Kante", "+15555553008")

    resp = await client.get("/api/v1/users", params={"q": "zida"})
    assert resp.status_code == 200
    names = {u["name"] for u in resp.json()}
    assert names == {"Zinedine Zidane"}

    # case-insensitive
    resp = await client.get("/api/v1/users", params={"q": "ZIDA"})
    assert {u["name"] for u in resp.json()} == {"Zinedine Zidane"}


async def test_list_users_no_query_returns_unfiltered(client):
    await make_user(client, "Alice", "+15555553009")
    await make_user(client, "Bob", "+15555553010")
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 200
    names = {u["name"] for u in resp.json()}
    assert {"Alice", "Bob"} <= names


async def test_list_users_search_below_min_length_rejected(client):
    resp = await client.get("/api/v1/users", params={"q": "a"})
    assert resp.status_code == 422
