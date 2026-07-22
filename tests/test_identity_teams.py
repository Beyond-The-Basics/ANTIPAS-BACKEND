"""Integration tests for the Identity & teams routers (require Postgres; see conftest)."""

import pytest

from tests.conftest import auth_header
from tests.conftest import make_team as create_team
from tests.conftest import make_user as create_user

pytestmark = pytest.mark.asyncio


async def test_create_user_and_duplicate_phone(client):
    user = await create_user(client, "Alice", "+15555550100")
    assert user["phone_verified"] is False
    dup = await client.post("/api/v1/users", json={"name": "Alice2", "phone": "+15555550100"})
    assert dup.status_code == 409


async def test_me_requires_auth_and_resolves(client):
    assert (await client.get("/api/v1/users/me")).status_code == 422  # missing X-User-Id header
    user = await create_user(client, "Bob", "+15555550101")
    me = await client.get("/api/v1/users/me", headers=auth_header(user["id"]))
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


async def test_create_team_makes_creator_captain(client):
    captain = await create_user(client, "Cap", "+15555550102")
    team = await create_team(client, captain["id"])
    assert team["is_adhoc"] is False and team["completed"] is False

    members = (await client.get(f"/api/v1/teams/{team['id']}/members")).json()
    assert len(members) == 1
    assert members[0]["user_id"] == captain["id"]
    assert members[0]["role"] == "captain"


async def test_captain_cannot_leave_without_transfer(client):
    captain = await create_user(client, "Cap", "+15555550103")
    team = await create_team(client, captain["id"])
    resp = await client.post(f"/api/v1/teams/{team['id']}/leave", headers=auth_header(captain["id"]))
    assert resp.status_code == 409


async def test_update_team_requires_membership(client):
    captain = await create_user(client, "Cap", "+15555550104")
    outsider = await create_user(client, "Nosy", "+15555550105")
    team = await create_team(client, captain["id"])

    ok = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"completed": True},
        headers=auth_header(captain["id"]),
    )
    assert ok.status_code == 200 and ok.json()["completed"] is True

    forbidden = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"name": "Hijacked"},
        headers=auth_header(outsider["id"]),
    )
    assert forbidden.status_code == 403


async def test_transfer_captain_and_role_management(client, db_session):
    from tests.conftest import add_member

    captain = await create_user(client, "Cap", "+15555550106")
    member = await create_user(client, "Mem", "+15555550107")
    team = await create_team(client, captain["id"])

    # Add a second member directly (the invite/accept flow is a later milestone).
    await add_member(db_session, team["id"], member["id"], role="member")

    # A plain member cannot promote anyone.
    denied = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{captain['id']}/role",
        json={"role": "admin"},
        headers=auth_header(member["id"]),
    )
    assert denied.status_code == 403

    # Captain promotes the member to admin.
    promoted = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}/role",
        json={"role": "admin"},
        headers=auth_header(captain["id"]),
    )
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"

    # Cannot set role to captain via this endpoint.
    bad = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}/role",
        json={"role": "captain"},
        headers=auth_header(captain["id"]),
    )
    assert bad.status_code == 422

    # Transfer captaincy; old captain becomes a regular member.
    transfer = await client.post(
        f"/api/v1/teams/{team['id']}/transfer-captain",
        json={"new_captain_user_id": member["id"]},
        headers=auth_header(captain["id"]),
    )
    assert transfer.status_code == 204

    roster = (await client.get(f"/api/v1/teams/{team['id']}/members")).json()
    members = {m["user_id"]: m["role"] for m in roster}
    assert members[member["id"]] == "captain"
    assert members[captain["id"]] == "member"

    # Now the old captain (a member) can leave.
    left = await client.post(f"/api/v1/teams/{team['id']}/leave", headers=auth_header(captain["id"]))
    assert left.status_code == 204
    remaining = (await client.get(f"/api/v1/teams/{team['id']}/members")).json()
    assert len(remaining) == 1
