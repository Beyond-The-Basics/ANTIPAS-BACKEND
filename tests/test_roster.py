"""Integration tests for RosterSearch + RosterApplication (require Postgres; see conftest)."""

import pytest

from tests.conftest import add_member, auth_header, make_team, make_user

pytestmark = pytest.mark.asyncio


async def publish_search(client, team_id, captain_id, city="Casablanca"):
    resp = await client.post(
        f"/api/v1/teams/{team_id}/roster-searches",
        json={"city": city},
        headers=auth_header(captain_id),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def apply(client, search_id, user_id):
    return await client.post(
        f"/api/v1/roster-searches/{search_id}/applications",
        headers=auth_header(user_id),
    )


async def invite(client, team_id, actor_id, user_id):
    return await client.post(
        f"/api/v1/teams/{team_id}/roster-invitations",
        json={"user_id": user_id},
        headers=auth_header(actor_id),
    )


async def team_member_ids(client, team_id):
    resp = await client.get(f"/api/v1/teams/{team_id}/members")
    return {m["user_id"] for m in resp.json()}


# --- RosterSearch -------------------------------------------------------------


async def test_publish_defaults_country_to_team(client):
    cap = await make_user(client, "Cap", "+15555553099")
    team = await make_team(client, cap["id"])  # country defaults to Morocco
    search = await publish_search(client, team["id"], cap["id"])
    assert search["country"] == "Morocco"


async def test_publish_requires_captain_or_admin(client):
    cap = await make_user(client, "Cap", "+15555553000")
    outsider = await make_user(client, "Out", "+15555553001")
    team = await make_team(client, cap["id"])

    search = await publish_search(client, team["id"], cap["id"])
    assert search["status"] == "open" and search["team_id"] == team["id"]

    denied = await client.post(
        f"/api/v1/teams/{team['id']}/roster-searches",
        json={"city": "Rabat"},
        headers=auth_header(outsider["id"]),
    )
    assert denied.status_code == 403


async def test_browse_filters_by_city_and_sport(client):
    cap = await make_user(client, "Cap", "+15555553002")
    soccer = await make_team(client, cap["id"], name="Kickers", sport="soccer")
    tennis = await make_team(client, cap["id"], name="Racket", sport="tennis")
    await publish_search(client, soccer["id"], cap["id"], city="Casablanca")
    await publish_search(client, tennis["id"], cap["id"], city="Casablanca")

    by_sport = await client.get("/api/v1/roster-searches", params={"sport": "soccer"})
    assert {s["team_id"] for s in by_sport.json()} == {soccer["id"]}

    by_city = await client.get("/api/v1/roster-searches", params={"city": "Casablanca"})
    assert {soccer["id"], tennis["id"]} == {s["team_id"] for s in by_city.json()}


async def test_get_search_404(client):
    import uuid

    resp = await client.get(f"/api/v1/roster-searches/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_close_search_then_cannot_close_again(client):
    cap = await make_user(client, "Cap", "+15555553003")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])

    closed = await client.post(
        f"/api/v1/roster-searches/{search['id']}/close", headers=auth_header(cap["id"])
    )
    assert closed.status_code == 204

    again = await client.post(f"/api/v1/roster-searches/{search['id']}/close", headers=auth_header(cap["id"]))
    assert again.status_code == 400

    # closed searches are not browsable
    listed = await client.get("/api/v1/roster-searches")
    assert search["id"] not in {s["id"] for s in listed.json()}


# --- player applies -> captain accepts ----------------------------------------


async def test_player_applies_and_captain_accepts_creates_membership(client):
    cap = await make_user(client, "Cap", "+15555553004")
    player = await make_user(client, "Player", "+15555553005")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])

    application = (await apply(client, search["id"], player["id"])).json()
    assert application["direction"] == "player_applied"
    assert application["status"] == "pending"
    assert player["id"] not in await team_member_ids(client, team["id"])

    accepted = await client.post(
        f"/api/v1/roster-applications/{application['id']}/accept",
        headers=auth_header(cap["id"]),
    )
    assert accepted.status_code == 200 and accepted.json()["status"] == "confirmed"
    assert player["id"] in await team_member_ids(client, team["id"])


async def test_apply_rejected_if_already_member(client, db_session):
    cap = await make_user(client, "Cap", "+15555553006")
    member = await make_user(client, "Mem", "+15555553007")
    team = await make_team(client, cap["id"])
    await add_member(db_session, team["id"], member["id"], role="member")
    search = await publish_search(client, team["id"], cap["id"])

    resp = await apply(client, search["id"], member["id"])
    assert resp.status_code == 400


async def test_duplicate_pending_application_conflicts(client):
    cap = await make_user(client, "Cap", "+15555553008")
    player = await make_user(client, "Player", "+15555553009")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])

    assert (await apply(client, search["id"], player["id"])).status_code == 201
    assert (await apply(client, search["id"], player["id"])).status_code == 409


async def test_random_user_cannot_accept_player_application(client):
    cap = await make_user(client, "Cap", "+15555553010")
    player = await make_user(client, "Player", "+15555553011")
    rando = await make_user(client, "Rando", "+15555553012")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])
    application = (await apply(client, search["id"], player["id"])).json()

    resp = await client.post(
        f"/api/v1/roster-applications/{application['id']}/accept",
        headers=auth_header(rando["id"]),
    )
    assert resp.status_code == 403


# --- captain invites -> player accepts ----------------------------------------


async def test_invite_and_player_accepts_creates_membership(client):
    cap = await make_user(client, "Cap", "+15555553013")
    player = await make_user(client, "Player", "+15555553014")
    team = await make_team(client, cap["id"])

    invited = (await invite(client, team["id"], cap["id"], player["id"])).json()
    assert invited["direction"] == "team_invited"
    assert invited["roster_search_id"] is None

    accepted = await client.post(
        f"/api/v1/roster-applications/{invited['id']}/accept",
        headers=auth_header(player["id"]),
    )
    assert accepted.status_code == 200
    assert player["id"] in await team_member_ids(client, team["id"])


async def test_captain_cannot_accept_own_invite(client):
    cap = await make_user(client, "Cap", "+15555553015")
    player = await make_user(client, "Player", "+15555553016")
    team = await make_team(client, cap["id"])
    invited = (await invite(client, team["id"], cap["id"], player["id"])).json()

    resp = await client.post(
        f"/api/v1/roster-applications/{invited['id']}/accept",
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 403


async def test_invite_unknown_user_404(client):
    import uuid

    cap = await make_user(client, "Cap", "+15555553017")
    team = await make_team(client, cap["id"])
    resp = await invite(client, team["id"], cap["id"], str(uuid.uuid4()))
    assert resp.status_code == 404


# --- withdraw authorization ---------------------------------------------------


async def test_withdraw_player_application_only_by_applicant(client):
    cap = await make_user(client, "Cap", "+15555553018")
    player = await make_user(client, "Player", "+15555553019")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])
    application = (await apply(client, search["id"], player["id"])).json()

    # captain cannot withdraw the player's application
    denied = await client.post(
        f"/api/v1/roster-applications/{application['id']}/withdraw",
        headers=auth_header(cap["id"]),
    )
    assert denied.status_code == 403

    ok = await client.post(
        f"/api/v1/roster-applications/{application['id']}/withdraw",
        headers=auth_header(player["id"]),
    )
    assert ok.status_code == 204


async def test_withdraw_invite_only_by_team(client):
    cap = await make_user(client, "Cap", "+15555553020")
    player = await make_user(client, "Player", "+15555553021")
    team = await make_team(client, cap["id"])
    invited = (await invite(client, team["id"], cap["id"], player["id"])).json()

    denied = await client.post(
        f"/api/v1/roster-applications/{invited['id']}/withdraw",
        headers=auth_header(player["id"]),
    )
    assert denied.status_code == 403

    ok = await client.post(
        f"/api/v1/roster-applications/{invited['id']}/withdraw",
        headers=auth_header(cap["id"]),
    )
    assert ok.status_code == 204


# --- reactivation & listings --------------------------------------------------


async def test_accept_reactivates_left_membership_without_duplicate(client, db_session):
    from sqlalchemy import func, select

    from app.models.team import TeamMembership

    cap = await make_user(client, "Cap", "+15555553022")
    player = await make_user(client, "Player", "+15555553023")
    team = await make_team(client, cap["id"])

    # player joins, then the captain removes them (membership -> left)
    await add_member(db_session, team["id"], player["id"], role="member")
    left = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{player['id']}",
        headers=auth_header(cap["id"]),
    )
    assert left.status_code == 204
    assert player["id"] not in await team_member_ids(client, team["id"])

    # re-invite and accept
    invited = (await invite(client, team["id"], cap["id"], player["id"])).json()
    await client.post(
        f"/api/v1/roster-applications/{invited['id']}/accept",
        headers=auth_header(player["id"]),
    )
    assert player["id"] in await team_member_ids(client, team["id"])

    # exactly one membership row for (team, player) — reactivated, not duplicated
    count = await db_session.scalar(
        select(func.count())
        .select_from(TeamMembership)
        .where(TeamMembership.team_id == team["id"], TeamMembership.user_id == player["id"])
    )
    assert count == 1


async def test_list_applications_views(client):
    cap = await make_user(client, "Cap", "+15555553024")
    player = await make_user(client, "Player", "+15555553025")
    team = await make_team(client, cap["id"])
    search = await publish_search(client, team["id"], cap["id"])
    application = (await apply(client, search["id"], player["id"])).json()

    # captain sees applicants for the search
    search_apps = await client.get(
        f"/api/v1/roster-searches/{search['id']}/applications",
        headers=auth_header(cap["id"]),
    )
    assert search_apps.status_code == 200
    assert application["id"] in {a["id"] for a in search_apps.json()}

    # a non-manager cannot list them
    denied = await client.get(
        f"/api/v1/roster-searches/{search['id']}/applications",
        headers=auth_header(player["id"]),
    )
    assert denied.status_code == 403

    # the player sees their own applications
    mine = await client.get("/api/v1/users/me/roster-applications", headers=auth_header(player["id"]))
    assert application["id"] in {a["id"] for a in mine.json()}
