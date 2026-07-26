"""Edge-case coverage for team listing and membership management (require Postgres; see conftest)."""

import uuid

import pytest

from tests.conftest import add_member, auth_header, make_team, make_user

pytestmark = pytest.mark.asyncio


async def members_by_user(client, team_id) -> dict[str, str]:
    resp = await client.get(f"/api/v1/teams/{team_id}/members")
    assert resp.status_code == 200
    return {m["user_id"]: m["role"] for m in resp.json()}


# --- teams: read paths --------------------------------------------------------


async def test_get_team_404(client):
    resp = await client.get(f"/api/v1/teams/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_list_teams_filters_by_sport(client):
    cap = await make_user(client, "Cap", "+15555552000")
    await make_team(client, cap["id"], name="Kickers", sport="soccer")
    await make_team(client, cap["id"], name="Racket", sport="tennis")

    soccer = await client.get("/api/v1/teams", params={"sport": "soccer"})
    assert soccer.status_code == 200
    sports = {t["sport"] for t in soccer.json()}
    assert sports == {"soccer"}


async def test_create_team_requires_auth(client):
    resp = await client.post("/api/v1/teams", json={"name": "NoAuth", "sport": "soccer"})
    assert resp.status_code == 401  # no bearer token and no stub header


# --- transfer-captain validation ---------------------------------------------


async def test_transfer_to_non_member_400(client):
    cap = await make_user(client, "Cap", "+15555552001")
    outsider = await make_user(client, "Out", "+15555552002")
    team = await make_team(client, cap["id"])
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/transfer-captain",
        json={"new_captain_user_id": outsider["id"]},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 400


async def test_transfer_to_self_400(client):
    cap = await make_user(client, "Cap", "+15555552003")
    team = await make_team(client, cap["id"])
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/transfer-captain",
        json={"new_captain_user_id": cap["id"]},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 400


async def test_non_captain_cannot_transfer(client, db_session):
    cap = await make_user(client, "Cap", "+15555552004")
    member = await make_user(client, "Mem", "+15555552005")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], member["id"], role="member")
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/transfer-captain",
        json={"new_captain_user_id": member["id"]},
        headers=auth_header(member["id"]),
    )
    assert resp.status_code == 403


# --- role management ----------------------------------------------------------


async def test_set_role_target_not_found_404(client):
    cap = await make_user(client, "Cap", "+15555552006")
    ghost = await make_user(client, "Ghost", "+15555552007")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{ghost['id']}/role",
        json={"role": "admin"},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 404


async def test_captain_demotes_admin(client, db_session):
    cap = await make_user(client, "Cap", "+15555552008")
    admin = await make_user(client, "Adm", "+15555552009")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], admin["id"], role="admin")

    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{admin['id']}/role",
        json={"role": "member"},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200 and resp.json()["role"] == "member"


async def test_captain_cannot_change_own_role(client):
    cap = await make_user(client, "Cap", "+15555552010")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/role",
        json={"role": "admin"},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 400


# --- remove member ------------------------------------------------------------


async def test_captain_removes_member(client, db_session):
    cap = await make_user(client, "Cap", "+15555552011")
    member = await make_user(client, "Mem", "+15555552012")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], member["id"], role="member")

    resp = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 204
    assert member["id"] not in await members_by_user(client, team["id"])


async def test_admin_removes_member_but_not_admin(client, db_session):
    cap = await make_user(client, "Cap", "+15555552013")
    admin = await make_user(client, "Adm", "+15555552014")
    admin2 = await make_user(client, "Adm2", "+15555552015")
    member = await make_user(client, "Mem", "+15555552016")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], admin["id"], role="admin")
    await add_member(db_session, team["id"], admin2["id"], role="admin")
    await add_member(db_session, team["id"], member["id"], role="member")

    # admin can remove a plain member
    ok = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=auth_header(admin["id"]),
    )
    assert ok.status_code == 204

    # admin cannot remove another admin
    denied = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{admin2['id']}",
        headers=auth_header(admin["id"]),
    )
    assert denied.status_code == 403


async def test_cannot_remove_captain(client, db_session):
    cap = await make_user(client, "Cap", "+15555552017")
    admin = await make_user(client, "Adm", "+15555552018")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], admin["id"], role="admin")

    resp = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}",
        headers=auth_header(admin["id"]),
    )
    assert resp.status_code == 400


async def test_outsider_cannot_remove(client, db_session):
    cap = await make_user(client, "Cap", "+15555552019")
    member = await make_user(client, "Mem", "+15555552020")
    outsider = await make_user(client, "Out", "+15555552021")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], member["id"], role="member")

    resp = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=auth_header(outsider["id"]),
    )
    assert resp.status_code == 403


# --- leave --------------------------------------------------------------------


async def test_leave_when_not_a_member_404(client):
    cap = await make_user(client, "Cap", "+15555552022")
    outsider = await make_user(client, "Out", "+15555552023")
    team = await make_team(client, cap["id"])
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/leave",
        headers=auth_header(outsider["id"]),
    )
    assert resp.status_code == 404


async def test_captain_sets_lineup_positions(client, db_session):
    cap = await make_user(client, "Cap", "+15555559200")
    p1 = await make_user(client, "P1", "+15555559201")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], p1["id"])

    resp = await client.put(
        f"/api/v1/teams/{team['id']}/lineup",
        json={"assignments": [
            {"user_id": cap["id"], "position": 0},
            {"user_id": p1["id"], "position": 3},
        ]},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    positions = {m["user_id"]: m["lineup_position"] for m in resp.json()}
    assert positions[cap["id"]] == 0
    assert positions[p1["id"]] == 3

    # benching sets it back to null
    resp = await client.put(
        f"/api/v1/teams/{team['id']}/lineup",
        json={"assignments": [{"user_id": p1["id"], "position": None}]},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200
    assert {m["user_id"]: m["lineup_position"] for m in resp.json()}[p1["id"]] is None


async def test_non_captain_cannot_set_lineup(client, db_session):
    cap = await make_user(client, "Cap", "+15555559210")
    admin = await make_user(client, "Adm", "+15555559211")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], admin["id"], role="admin")

    resp = await client.put(
        f"/api/v1/teams/{team['id']}/lineup",
        json={"assignments": [{"user_id": admin["id"], "position": 0}]},
        headers=auth_header(admin["id"]),
    )
    assert resp.status_code == 403


async def test_lineup_rejects_non_member(client, db_session):
    cap = await make_user(client, "Cap", "+15555559220")
    outsider = await make_user(client, "Out", "+15555559221")
    team = await make_team(client, cap["id"])
    resp = await client.put(
        f"/api/v1/teams/{team['id']}/lineup",
        json={"assignments": [{"user_id": outsider["id"], "position": 0}]},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 404
