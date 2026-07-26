"""Integration tests for GuestSearch + GuestApplication + MatchGuestParticipant (require Postgres)."""

import uuid

import pytest
from sqlalchemy import func, select

from app.models.team import TeamMembership
from tests.conftest import auth_header, completed_team, make_user

pytestmark = pytest.mark.asyncio


async def a_confirmed_match(client, db_session, suffix: str):
    """Two completed teams run Flow 2 to a confirmed match. Returns (match, capA, capB, teamA, teamB)."""
    cap_a = await make_user(client, "CapA", f"+1666{suffix}00")
    cap_b = await make_user(client, "CapB", f"+1666{suffix}01")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (
        await client.post(
            f"/api/v1/teams/{home['id']}/opponent-searches",
            # No game_type_id — inherited from the (already-completed) publishing team.
            json={"city": "Casablanca", "pitch": "Stade X", "date": "2026-09-01T18:00:00"},
            headers=auth_header(cap_a["id"]),
        )
    ).json()
    app_b = (
        await client.post(
            f"/api/v1/opponent-searches/{search['id']}/applications",
            json={"responding_team_id": away["id"]},
            headers=auth_header(cap_b["id"]),
        )
    ).json()
    # accept the challenge, then the away captain agrees to the home team's seeded terms.
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    match = (
        await client.post(
            f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
        )
    ).json()
    return match, cap_a, cap_b, home, away


async def publish_guest(client, match_id, team_id, actor_id):
    return await client.post(
        f"/api/v1/matches/{match_id}/guest-searches",
        json={"team_id": team_id},
        headers=auth_header(actor_id),
    )


# --- publish gating -----------------------------------------------------------


async def test_publish_requires_confirmed_match_and_team_in_it(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "10")
    stranger_cap = await make_user(client, "SCap", "+16661010102")
    outside_team = await completed_team(client, db_session, stranger_cap, "Outsiders")

    ok = await publish_guest(client, match["id"], home["id"], cap_a["id"])
    assert ok.status_code == 201, ok.text
    assert ok.json()["city"] == "Casablanca" and ok.json()["status"] == "open"

    # a team not in the match cannot publish against it
    bad_team = await publish_guest(client, match["id"], outside_team["id"], stranger_cap["id"])
    assert bad_team.status_code == 400

    # cancel the match -> can no longer publish
    await client.post(f"/api/v1/matches/{match['id']}/cancel", headers=auth_header(cap_a["id"]))
    after_cancel = await publish_guest(client, match["id"], away["id"], cap_b["id"])
    assert after_cancel.status_code == 400


async def test_publish_requires_manager(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "11")
    outsider = await make_user(client, "Out", "+16661111102")
    resp = await publish_guest(client, match["id"], home["id"], outsider["id"])
    assert resp.status_code == 403


# --- player applies -> team accepts -> participant -----------------------------


async def test_apply_accept_creates_participant_not_membership(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "12")
    guest = await make_user(client, "Guest", "+16661212102")
    search = (await publish_guest(client, match["id"], home["id"], cap_a["id"])).json()

    application = (
        await client.post(
            f"/api/v1/guest-searches/{search['id']}/applications",
            headers=auth_header(guest["id"]),
        )
    ).json()
    assert application["direction"] == "player_applied"

    accepted = await client.post(
        f"/api/v1/guest-applications/{application['id']}/accept",
        headers=auth_header(cap_a["id"]),
    )
    assert accepted.status_code == 200
    participant = accepted.json()
    assert participant["user_id"] == guest["id"] and participant["team_id"] == home["id"]

    # participant is listed for the match
    guests = await client.get(f"/api/v1/matches/{match['id']}/guests")
    assert guest["id"] in {g["user_id"] for g in guests.json()}

    # NO TeamMembership was created (one-off only)
    membership_count = await db_session.scalar(
        select(func.count())
        .select_from(TeamMembership)
        .where(TeamMembership.team_id == home["id"], TeamMembership.user_id == guest["id"])
    )
    assert membership_count == 0

    # the guest search is now closed
    search_now = await client.get(f"/api/v1/guest-searches/{search['id']}")
    assert search_now.json()["status"] == "confirmed"


async def test_accept_auto_declines_other_applicants(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "13")
    g1 = await make_user(client, "G1", "+16661313102")
    g2 = await make_user(client, "G2", "+16661313103")
    search = (await publish_guest(client, match["id"], home["id"], cap_a["id"])).json()

    a1 = (
        await client.post(
            f"/api/v1/guest-searches/{search['id']}/applications", headers=auth_header(g1["id"])
        )
    ).json()
    a2 = (
        await client.post(
            f"/api/v1/guest-searches/{search['id']}/applications", headers=auth_header(g2["id"])
        )
    ).json()

    await client.post(f"/api/v1/guest-applications/{a1['id']}/accept", headers=auth_header(cap_a["id"]))

    apps = await client.get(
        f"/api/v1/guest-searches/{search['id']}/applications", headers=auth_header(cap_a["id"])
    )
    statuses = {a["id"]: a["status"] for a in apps.json()}
    assert statuses[a1["id"]] == "confirmed"
    assert statuses[a2["id"]] == "declined"


async def test_player_in_match_cannot_guest(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "14")
    search = (await publish_guest(client, match["id"], home["id"], cap_a["id"])).json()
    # cap_b is a member (captain) of the away team in this match
    resp = await client.post(
        f"/api/v1/guest-searches/{search['id']}/applications", headers=auth_header(cap_b["id"])
    )
    assert resp.status_code == 400


# --- team invites a player directly -------------------------------------------


async def test_invite_and_player_accepts(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "15")
    guest = await make_user(client, "Guest", "+16661515102")

    invited = (
        await client.post(
            f"/api/v1/matches/{match['id']}/guest-invitations",
            json={"team_id": home["id"], "user_id": guest["id"]},
            headers=auth_header(cap_a["id"]),
        )
    ).json()
    assert invited["direction"] == "team_invited" and invited["guest_search_id"] is None

    # captain cannot accept on the player's behalf
    denied = await client.post(
        f"/api/v1/guest-applications/{invited['id']}/accept", headers=auth_header(cap_a["id"])
    )
    assert denied.status_code == 403

    accepted = await client.post(
        f"/api/v1/guest-applications/{invited['id']}/accept", headers=auth_header(guest["id"])
    )
    assert accepted.status_code == 200
    guests = await client.get(f"/api/v1/matches/{match['id']}/guests")
    assert guest["id"] in {g["user_id"] for g in guests.json()}


async def test_withdraw_and_list_mine(client, db_session):
    match, cap_a, cap_b, home, away = await a_confirmed_match(client, db_session, "16")
    guest = await make_user(client, "Guest", "+16661616102")
    search = (await publish_guest(client, match["id"], home["id"], cap_a["id"])).json()
    application = (
        await client.post(
            f"/api/v1/guest-searches/{search['id']}/applications", headers=auth_header(guest["id"])
        )
    ).json()

    mine = await client.get("/api/v1/users/me/guest-applications", headers=auth_header(guest["id"]))
    assert application["id"] in {a["id"] for a in mine.json()}

    # the team cannot withdraw the player's application; the applicant can
    denied = await client.post(
        f"/api/v1/guest-applications/{application['id']}/withdraw", headers=auth_header(cap_a["id"])
    )
    assert denied.status_code == 403
    ok = await client.post(
        f"/api/v1/guest-applications/{application['id']}/withdraw", headers=auth_header(guest["id"])
    )
    assert ok.status_code == 204


async def test_get_guest_search_404(client):
    resp = await client.get(f"/api/v1/guest-searches/{uuid.uuid4()}")
    assert resp.status_code == 404
