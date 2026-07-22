"""Integration tests for OpponentSearch + OpponentApplication + Match (require Postgres)."""

import uuid

import pytest
from sqlalchemy import select

from app.models.game_type import GameType
from tests.conftest import auth_header, make_team, make_user

pytestmark = pytest.mark.asyncio


async def a_game_type(db_session, sport: str = "soccer") -> str:
    """Fetch a seeded-style GameType id, creating one if the test DB has none."""
    gt = await db_session.scalar(select(GameType).where(GameType.sport == sport))
    if gt is None:
        gt = GameType(sport=sport, label="5v5" if sport == "soccer" else "singles")
        db_session.add(gt)
        await db_session.commit()
        await db_session.refresh(gt)
    return str(gt.id)


async def completed_team(client, db_session, captain, name, sport="soccer") -> dict:
    team = await make_team(client, captain["id"], name=name, sport=sport)
    # mark completed (captain/admin only) — required to publish/respond in Flow 2
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"completed": True},
        headers=auth_header(captain["id"]),
    )
    assert resp.status_code == 200 and resp.json()["completed"] is True
    return team


async def publish(client, db_session, team_id, captain_id, city="Casablanca", sport="soccer"):
    resp = await client.post(
        f"/api/v1/teams/{team_id}/opponent-searches",
        json={
            "game_type_id": await a_game_type(db_session, sport),
            "city": city,
            "pitch": "Stade Municipal",
            "date": "2026-09-01",
        },
        headers=auth_header(captain_id),
    )
    return resp


# --- publish gating -----------------------------------------------------------


async def test_publish_requires_completed_team(client, db_session):
    cap = await make_user(client, "Cap", "+15555554000")
    team = await make_team(client, cap["id"])  # not completed
    resp = await publish(client, db_session, team["id"], cap["id"])
    assert resp.status_code == 400

    await client.patch(
        f"/api/v1/teams/{team['id']}", json={"completed": True}, headers=auth_header(cap["id"])
    )
    ok = await publish(client, db_session, team["id"], cap["id"])
    assert ok.status_code == 201
    assert ok.json()["status"] == "open" and ok.json()["sport"] == "soccer"


async def test_publish_rejects_game_type_of_other_sport(client, db_session):
    cap = await make_user(client, "Cap", "+15555554001")
    team = await completed_team(client, db_session, cap, "Kickers", sport="soccer")
    tennis_gt = await a_game_type(db_session, sport="tennis")
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/opponent-searches",
        json={
            "game_type_id": tennis_gt,
            "city": "Casablanca",
            "pitch": "Court 1",
            "date": "2026-09-01",
        },
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 400


async def test_publish_requires_manager(client, db_session):
    cap = await make_user(client, "Cap", "+15555554002")
    outsider = await make_user(client, "Out", "+15555554003")
    team = await completed_team(client, db_session, cap, "Kickers")
    resp = await publish(client, db_session, team["id"], outsider["id"])
    assert resp.status_code == 403


# --- browse -------------------------------------------------------------------


async def test_browse_filters_by_sport(client, db_session):
    cap = await make_user(client, "Cap", "+15555554004")
    soccer = await completed_team(client, db_session, cap, "Kickers", sport="soccer")
    tennis = await completed_team(client, db_session, cap, "Racket", sport="tennis")
    await publish(client, db_session, soccer["id"], cap["id"], sport="soccer")
    await publish(client, db_session, tennis["id"], cap["id"], sport="tennis")

    resp = await client.get("/api/v1/opponent-searches", params={"sport": "soccer"})
    assert {s["team_id"] for s in resp.json()} == {soccer["id"]}


# --- apply rules --------------------------------------------------------------


async def test_apply_rejections(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554005")
    cap_b = await make_user(client, "CapB", "+15555554006")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    incomplete = await make_team(client, cap_b["id"], name="Rookies")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()

    # cannot respond with your own (publishing) team
    own = await client.post(
        f"/api/v1/opponent-searches/{search['id']}/applications",
        json={"responding_team_id": home["id"]},
        headers=auth_header(cap_a["id"]),
    )
    assert own.status_code == 400

    # responding team must be completed
    not_done = await client.post(
        f"/api/v1/opponent-searches/{search['id']}/applications",
        json={"responding_team_id": incomplete["id"]},
        headers=auth_header(cap_b["id"]),
    )
    assert not_done.status_code == 400

    # valid application
    ok = await client.post(
        f"/api/v1/opponent-searches/{search['id']}/applications",
        json={"responding_team_id": away["id"]},
        headers=auth_header(cap_b["id"]),
    )
    assert ok.status_code == 201


async def test_apply_requires_manager_of_responding_team(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554007")
    cap_b = await make_user(client, "CapB", "+15555554008")
    stranger = await make_user(client, "Stranger", "+15555554009")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()

    resp = await client.post(
        f"/api/v1/opponent-searches/{search['id']}/applications",
        json={"responding_team_id": away["id"]},
        headers=auth_header(stranger["id"]),
    )
    assert resp.status_code == 403


# --- confirm -> Match ---------------------------------------------------------


async def test_confirm_creates_match_and_auto_declines(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554010")
    cap_b = await make_user(client, "CapB", "+15555554011")
    cap_c = await make_user(client, "CapC", "+15555554012")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    other = await completed_team(client, db_session, cap_c, "Other")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()

    app_b = (
        await client.post(
            f"/api/v1/opponent-searches/{search['id']}/applications",
            json={"responding_team_id": away["id"]},
            headers=auth_header(cap_b["id"]),
        )
    ).json()
    app_c = (
        await client.post(
            f"/api/v1/opponent-searches/{search['id']}/applications",
            json={"responding_team_id": other["id"]},
            headers=auth_header(cap_c["id"]),
        )
    ).json()

    # only the publisher confirms
    denied = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/confirm",
        headers=auth_header(cap_b["id"]),
    )
    assert denied.status_code == 403

    confirmed = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/confirm",
        headers=auth_header(cap_a["id"]),
    )
    assert confirmed.status_code == 200
    match = confirmed.json()
    assert match["team_a_id"] == home["id"] and match["team_b_id"] == away["id"]
    assert match["status"] == "confirmed"

    # search closed; other application auto-declined
    search_now = await client.get(f"/api/v1/opponent-searches/{search['id']}")
    assert search_now.json()["status"] == "confirmed"

    apps = await client.get(
        f"/api/v1/opponent-searches/{search['id']}/applications",
        headers=auth_header(cap_a["id"]),
    )
    statuses = {a["id"]: a["status"] for a in apps.json()}
    assert statuses[app_b["id"]] == "confirmed"
    assert statuses[app_c["id"]] == "declined"

    # search shows in both teams' matches
    home_matches = await client.get(f"/api/v1/teams/{home['id']}/matches")
    away_matches = await client.get(f"/api/v1/teams/{away['id']}/matches")
    assert match["id"] in {m["id"] for m in home_matches.json()}
    assert match["id"] in {m["id"] for m in away_matches.json()}


async def test_cannot_confirm_twice(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554013")
    cap_b = await make_user(client, "CapB", "+15555554014")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = (
        await client.post(
            f"/api/v1/opponent-searches/{search['id']}/applications",
            json={"responding_team_id": away["id"]},
            headers=auth_header(cap_b["id"]),
        )
    ).json()
    first = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/confirm", headers=auth_header(cap_a["id"])
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/confirm", headers=auth_header(cap_a["id"])
    )
    assert second.status_code == 400


# --- Match lifecycle ----------------------------------------------------------


async def confirmed_match(client, db_session, suffix: str) -> tuple[dict, dict, dict]:
    cap_a = await make_user(client, "CapA", f"+1555555{suffix}0")
    cap_b = await make_user(client, "CapB", f"+1555555{suffix}1")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = (
        await client.post(
            f"/api/v1/opponent-searches/{search['id']}/applications",
            json={"responding_team_id": away["id"]},
            headers=auth_header(cap_b["id"]),
        )
    ).json()
    match = (
        await client.post(
            f"/api/v1/opponent-applications/{app_b['id']}/confirm",
            headers=auth_header(cap_a["id"]),
        )
    ).json()
    return match, cap_a, cap_b


async def test_cancel_records_side(client, db_session):
    match, cap_a, cap_b = await confirmed_match(client, db_session, "4015")
    resp = await client.post(f"/api/v1/matches/{match['id']}/cancel", headers=auth_header(cap_b["id"]))
    assert resp.status_code == 200 and resp.json()["status"] == "cancelled_by_b"


async def test_cancel_requires_manager(client, db_session):
    match, cap_a, cap_b = await confirmed_match(client, db_session, "4016")
    outsider = await make_user(client, "Out", "+15555554099")
    resp = await client.post(f"/api/v1/matches/{match['id']}/cancel", headers=auth_header(outsider["id"]))
    assert resp.status_code == 403


async def test_mark_played_then_cannot_cancel(client, db_session):
    match, cap_a, cap_b = await confirmed_match(client, db_session, "4017")
    played = await client.post(f"/api/v1/matches/{match['id']}/played", headers=auth_header(cap_a["id"]))
    assert played.status_code == 200 and played.json()["status"] == "played"

    cancel = await client.post(f"/api/v1/matches/{match['id']}/cancel", headers=auth_header(cap_a["id"]))
    assert cancel.status_code == 400


async def test_get_match_404(client):
    resp = await client.get(f"/api/v1/matches/{uuid.uuid4()}")
    assert resp.status_code == 404
