"""Pitch catalog: team-scoped venue creation, and the visibility rule for picking one during a
negotiation (own team + the opponent's + anyone's neutral pitches)."""

import pytest

from tests.conftest import auth_header, completed_team, make_user

pytestmark = pytest.mark.asyncio


async def publish(client, db_session, team_id, captain_id):
    resp = await client.post(
        f"/api/v1/teams/{team_id}/opponent-searches",
        json={"city": "Casablanca", "pitch": "Stade Municipal", "date": "2026-09-01T18:00:00"},
        headers=auth_header(captain_id),
    )
    return resp.json()


async def _apply(client, search_id, team_id, cap_id):
    return (
        await client.post(
            f"/api/v1/opponent-searches/{search_id}/applications",
            json={"responding_team_id": team_id},
            headers=auth_header(cap_id),
        )
    ).json()


async def test_create_pitch_requires_captain_or_admin(client, db_session):
    cap = await make_user(client, "Cap", "+15555555100")
    stranger = await make_user(client, "Str", "+15555555101")
    team = await completed_team(client, db_session, cap, "Home")

    denied = await client.post(
        f"/api/v1/teams/{team['id']}/pitches",
        json={"name": "Stade Père Jégo", "city": "Casablanca"},
        headers=auth_header(stranger["id"]),
    )
    assert denied.status_code == 403

    ok = await client.post(
        f"/api/v1/teams/{team['id']}/pitches",
        json={"name": "Stade Père Jégo", "city": "Casablanca", "price_per_hour": 180},
        headers=auth_header(cap["id"]),
    )
    assert ok.status_code == 201
    body = ok.json()
    assert body["team_id"] == team["id"]
    assert body["name"] == "Stade Père Jégo"
    assert body["price_per_hour"] == 180
    assert body["is_neutral"] is False


async def test_negotiation_pitches_include_own_opponent_and_neutral_only(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555555110")
    cap_b = await make_user(client, "CapB", "+15555555111")
    cap_c = await make_user(client, "CapC", "+15555555112")
    stranger = await make_user(client, "Str", "+15555555113")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    other = await completed_team(client, db_session, cap_c, "Other")

    search = await publish(client, db_session, home["id"], cap_a["id"])
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"]))

    home_pitch = (
        await client.post(
            f"/api/v1/teams/{home['id']}/pitches",
            json={"name": "Home Pitch", "city": "Casablanca"},
            headers=auth_header(cap_a["id"]),
        )
    ).json()
    away_pitch = (
        await client.post(
            f"/api/v1/teams/{away['id']}/pitches",
            json={"name": "Away Pitch", "city": "Mohammédia"},
            headers=auth_header(cap_b["id"]),
        )
    ).json()
    neutral_pitch = (
        await client.post(
            f"/api/v1/teams/{other['id']}/pitches",
            json={"name": "Complexe OCP", "city": "Casablanca", "is_neutral": True},
            headers=auth_header(cap_c["id"]),
        )
    ).json()
    # A pitch belonging to an unrelated team that is NOT neutral must stay invisible.
    private_other_pitch = (
        await client.post(
            f"/api/v1/teams/{other['id']}/pitches",
            json={"name": "Other's Private Pitch", "city": "Rabat"},
            headers=auth_header(cap_c["id"]),
        )
    ).json()

    listed = await client.get(
        f"/api/v1/opponent-applications/{app_b['id']}/pitches", headers=auth_header(cap_a["id"])
    )
    assert listed.status_code == 200
    ids = {p["id"] for p in listed.json()}
    assert ids == {home_pitch["id"], away_pitch["id"], neutral_pitch["id"]}
    assert private_other_pitch["id"] not in ids

    blocked = await client.get(
        f"/api/v1/opponent-applications/{app_b['id']}/pitches", headers=auth_header(stranger["id"])
    )
    assert blocked.status_code == 403
