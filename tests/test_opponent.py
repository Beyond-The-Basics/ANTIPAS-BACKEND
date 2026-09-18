"""Integration tests for OpponentSearch + OpponentApplication + Match (require Postgres)."""

import uuid

import pytest

from tests.conftest import auth_header, completed_team, make_team, make_user

pytestmark = pytest.mark.asyncio


async def publish(client, db_session, team_id, captain_id, city="Casablanca"):
    # No game_type_id — the search inherits it from the (already-completed, already-lineup-set)
    # publishing team. See tests/test_team_profile.py for the game_type_id-at-team-level rules.
    resp = await client.post(
        f"/api/v1/teams/{team_id}/opponent-searches",
        json={"city": city, "pitch": "Stade Municipal", "date": "2026-09-01T18:00:00"},
        headers=auth_header(captain_id),
    )
    return resp


# --- publish gating -----------------------------------------------------------


async def test_publish_requires_completed_team(client, db_session):
    cap = await make_user(client, "Cap", "+15555554000")
    team = await make_team(client, cap["id"])  # not completed, no lineup set
    resp = await publish(client, db_session, team["id"], cap["id"])
    assert resp.status_code == 400


async def test_publish_inherits_teams_game_type(client, db_session):
    cap = await make_user(client, "Cap", "+15555554001")
    team = await completed_team(client, db_session, cap, "Kickers", sport="soccer")
    ok = await publish(client, db_session, team["id"], cap["id"])
    assert ok.status_code == 201
    assert ok.json()["status"] == "open" and ok.json()["sport"] == "soccer"
    assert ok.json()["game_type_id"] == team["game_type_id"]


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
    await publish(client, db_session, soccer["id"], cap["id"])
    await publish(client, db_session, tennis["id"], cap["id"])

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


# --- negotiation: accept -> propose -> agree -> Match -------------------------


async def _apply(client, search_id, team_id, cap_id):
    return (
        await client.post(
            f"/api/v1/opponent-searches/{search_id}/applications",
            json={"responding_team_id": team_id},
            headers=auth_header(cap_id),
        )
    ).json()


async def test_accept_then_agree_creates_match_and_auto_declines(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554010")
    cap_b = await make_user(client, "CapB", "+15555554011")
    cap_c = await make_user(client, "CapC", "+15555554012")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    other = await completed_team(client, db_session, cap_c, "Other")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()

    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    app_c = await _apply(client, search["id"], other["id"], cap_c["id"])

    # only the publisher accepts the challenge
    denied = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_b["id"])
    )
    assert denied.status_code == 403

    accepted = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    # the search's terms seed the first proposal, made by the home (publishing) team
    assert accepted.json()["proposed_by_team_id"] == home["id"]

    # the proposer can't agree to their own proposal — the other team must
    self_agree = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_a["id"])
    )
    assert self_agree.status_code == 400

    agreed = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
    )
    assert agreed.status_code == 200
    match = agreed.json()
    assert match["team_a_id"] == home["id"] and match["team_b_id"] == away["id"]
    assert match["status"] == "confirmed"

    # search closed; the other pending application auto-declined
    search_now = await client.get(f"/api/v1/opponent-searches/{search['id']}")
    assert search_now.json()["status"] == "confirmed"
    apps = await client.get(
        f"/api/v1/opponent-searches/{search['id']}/applications", headers=auth_header(cap_a["id"])
    )
    statuses = {a["id"]: a["status"] for a in apps.json()}
    assert statuses[app_b["id"]] == "confirmed"
    assert statuses[app_c["id"]] == "declined"

    home_matches = await client.get(f"/api/v1/teams/{home['id']}/matches")
    away_matches = await client.get(f"/api/v1/teams/{away['id']}/matches")
    assert match["id"] in {m["id"] for m in home_matches.json()}
    assert match["id"] in {m["id"] for m in away_matches.json()}


async def test_propose_flips_who_must_agree_and_sets_match_terms(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554020")
    cap_b = await make_user(client, "CapB", "+15555554021")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    # away counter-proposes new terms — now home must be the one to agree
    prop = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/propose",
        json={"date": "2026-09-05T20:30:00", "pitch": "Complexe Sportif"},
        headers=auth_header(cap_b["id"]),
    )
    assert prop.status_code == 200 and prop.json()["proposed_by_team_id"] == away["id"]

    # away (proposer) can't agree now
    assert (
        await client.post(
            f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
        )
    ).status_code == 400

    match = (
        await client.post(
            f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_a["id"])
        )
    ).json()
    # The negotiated terms flow into the match (the exact time is normalized to UTC on storage;
    # the client renders it back in local time).
    assert match["pitch"] == "Complexe Sportif"
    assert match["date"].startswith("2026-09-05")


async def test_only_negotiating_teams_can_message(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554030")
    cap_b = await make_user(client, "CapB", "+15555554031")
    stranger = await make_user(client, "Str", "+15555554032")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    sent = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/messages",
        json={"body": "Can we push to 20:30?"},
        headers=auth_header(cap_b["id"]),
    )
    assert sent.status_code == 201

    blocked = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/messages",
        json={"body": "hi"},
        headers=auth_header(stranger["id"]),
    )
    assert blocked.status_code == 403

    listed = await client.get(
        f"/api/v1/opponent-applications/{app_b['id']}/messages", headers=auth_header(cap_a["id"])
    )
    assert [m["body"] for m in listed.json()] == ["Can we push to 20:30?"]


async def test_proposal_history_records_seed_and_counters(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554040")
    cap_b = await make_user(client, "CapB", "+15555554041")
    stranger = await make_user(client, "Str", "+15555554042")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    # accepting seeds the first history entry from the search's own terms
    seeded = await client.get(
        f"/api/v1/opponent-applications/{app_b['id']}/proposals", headers=auth_header(cap_a["id"])
    )
    assert seeded.status_code == 200
    assert len(seeded.json()) == 1
    first = seeded.json()[0]
    assert first["proposed_by_team_id"] == home["id"]
    assert first["pitch"] == "Stade Municipal"
    assert first["end_date"] is None and first["pitch_address"] is None

    # away counters with a full time range + pitch address
    countered = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/propose",
        json={
            "date": "2026-09-05T18:30:00",
            "end_date": "2026-09-05T20:00:00",
            "pitch": "Complexe Sportif OCP",
            "pitch_address": "Ain Sebaa, Casablanca",
        },
        headers=auth_header(cap_b["id"]),
    )
    assert countered.status_code == 200
    assert countered.json()["proposed_end_date"] is not None
    assert countered.json()["proposed_pitch_address"] == "Ain Sebaa, Casablanca"

    history = (
        await client.get(
            f"/api/v1/opponent-applications/{app_b['id']}/proposals", headers=auth_header(cap_b["id"])
        )
    ).json()
    assert len(history) == 2
    assert history[0]["proposed_by_team_id"] == home["id"]
    assert history[1]["proposed_by_team_id"] == away["id"]
    assert history[1]["pitch_address"] == "Ain Sebaa, Casablanca"

    # a non-member is blocked from reading the history, same as chat
    blocked = await client.get(
        f"/api/v1/opponent-applications/{app_b['id']}/proposals", headers=auth_header(stranger["id"])
    )
    assert blocked.status_code == 403


async def test_cannot_agree_twice(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554013")
    cap_b = await make_user(client, "CapB", "+15555554014")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    first = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
    )
    assert first.status_code == 200
    second = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
    )
    assert second.status_code == 400


async def test_decline_releases_the_search_for_another_challenger(client, db_session):
    """Declining is the way out of a negotiation that is not converging.

    The search stays OPEN, so the block `accept_challenge` puts on a second negotiation lifts and
    the publishing team can take a different challenger.
    """
    cap_a = await make_user(client, "CapA", "+15555554101")
    cap_b = await make_user(client, "CapB", "+15555554102")
    cap_c = await make_user(client, "CapC", "+15555554103")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    third = await completed_team(client, db_session, cap_c, "Third")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()

    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    app_c = await _apply(client, search["id"], third["id"], cap_c["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    # While B is under negotiation, C cannot be accepted.
    blocked = await client.post(
        f"/api/v1/opponent-applications/{app_c['id']}/accept", headers=auth_header(cap_a["id"])
    )
    assert blocked.status_code == 409

    declined = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )
    assert declined.status_code == 204, declined.text

    after = await client.get(f"/api/v1/opponent-searches/{search['id']}")
    assert after.json()["status"] == "open"

    accepted = await client.post(
        f"/api/v1/opponent-applications/{app_c['id']}/accept", headers=auth_header(cap_a["id"])
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"


async def test_accepting_takes_the_search_off_the_board_and_declining_puts_it_back(
    client, db_session
):
    """A search under negotiation stops being browsable, then comes back if the talks collapse.

    Listing it while a negotiation is live only invites challenges that `accept_challenge` is
    guaranteed to reject with a 409.
    """
    cap_a = await make_user(client, "CapA", "+15555554111")
    cap_b = await make_user(client, "CapB", "+15555554112")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"], city="Tangier")).json()

    def ids(resp):
        return [s["id"] for s in resp.json()]

    listed = await client.get("/api/v1/opponent-searches?city=Tangier")
    assert search["id"] in ids(listed)

    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    during = await client.get("/api/v1/opponent-searches?city=Tangier")
    assert search["id"] not in ids(during), "a search under negotiation must not be browsable"

    # Hidden from the board, but still readable by id — the two teams' pages depend on that.
    detail = await client.get(f"/api/v1/opponent-searches/{search['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "open"

    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )

    after = await client.get("/api/v1/opponent-searches?city=Tangier")
    assert search["id"] in ids(after), "declining must put the search back on the board"


async def test_agreeing_keeps_the_search_off_the_board(client, db_session):
    """Confirmed is terminal: `agree` closes the search, so it stays gone rather than returning."""
    cap_a = await make_user(client, "CapA", "+15555554113")
    cap_b = await make_user(client, "CapB", "+15555554114")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"], city="Agadir")).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    agreed = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
    )
    assert agreed.status_code == 200

    listed = await client.get("/api/v1/opponent-searches?city=Agadir")
    assert search["id"] not in [s["id"] for s in listed.json()]


async def test_either_team_can_decline(client, db_session):
    """The challenger can walk away too, not just the team that accepted the challenge."""
    cap_a = await make_user(client, "CapA", "+15555554104")
    cap_b = await make_user(client, "CapB", "+15555554105")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    resp = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_b["id"])
    )
    assert resp.status_code == 204, resp.text


async def test_decline_requires_a_live_negotiation_and_a_manager(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554106")
    cap_b = await make_user(client, "CapB", "+15555554107")
    outsider = await make_user(client, "Outsider", "+15555554108")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])

    # Still PENDING, so there is no negotiation to decline yet.
    too_early = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )
    assert too_early.status_code == 400

    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )

    stranger = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(outsider["id"])
    )
    assert stranger.status_code == 403

    first = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )
    assert first.status_code == 204
    # Declining twice is no longer a live negotiation either.
    again = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )
    assert again.status_code == 400


async def test_cannot_agree_after_declining(client, db_session):
    cap_a = await make_user(client, "CapA", "+15555554109")
    cap_b = await make_user(client, "CapB", "+15555554110")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/decline", headers=auth_header(cap_a["id"])
    )

    resp = await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
    )
    assert resp.status_code == 400


# --- Match lifecycle ----------------------------------------------------------


async def confirmed_match(client, db_session, suffix: str) -> tuple[dict, dict, dict]:
    cap_a = await make_user(client, "CapA", f"+1555555{suffix}0")
    cap_b = await make_user(client, "CapB", f"+1555555{suffix}1")
    home = await completed_team(client, db_session, cap_a, "Home")
    away = await completed_team(client, db_session, cap_b, "Away")
    search = (await publish(client, db_session, home["id"], cap_a["id"])).json()
    app_b = await _apply(client, search["id"], away["id"], cap_b["id"])
    await client.post(
        f"/api/v1/opponent-applications/{app_b['id']}/accept", headers=auth_header(cap_a["id"])
    )
    # home's terms seed the proposal, so the away captain agrees to finalize.
    match = (
        await client.post(
            f"/api/v1/opponent-applications/{app_b['id']}/agree", headers=auth_header(cap_b["id"])
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
