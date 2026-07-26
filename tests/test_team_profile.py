"""Team profile fields (description/country/city) and the name-search used to invite by name."""

import pytest

from tests.conftest import a_game_type, add_member, auth_header, completed_team, make_team, make_user

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


# --- lineup type (game_type_id) ------------------------------------------------


async def test_set_lineup_type(client, db_session):
    cap = await make_user(client, "Cap", "+15555553011")
    team = await make_team(client, cap["id"], sport="soccer")
    gt = await a_game_type(db_session, sport="soccer")
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(gt.id)},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["game_type_id"] == str(gt.id)
    # not completed yet — setting the lineup alone doesn't complete the team
    assert resp.json()["completed"] is False


async def test_lineup_type_must_match_team_sport(client, db_session):
    cap = await make_user(client, "Cap", "+15555553012")
    team = await make_team(client, cap["id"], sport="soccer")
    tennis_gt = await a_game_type(db_session, sport="tennis")
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(tennis_gt.id)},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 400


async def test_lineup_type_unknown_id_404s(client):
    import uuid

    cap = await make_user(client, "Cap", "+15555553013")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(uuid.uuid4())},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 404


# --- completion requires a full lineup -----------------------------------------


async def test_cannot_complete_without_lineup_type(client):
    cap = await make_user(client, "Cap", "+15555553014")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}", json={"completed": True}, headers=auth_header(cap["id"])
    )
    assert resp.status_code == 400
    assert "lineup" in resp.json()["detail"].lower()


async def test_captain_can_complete_with_lineup_but_short_roster(client, db_session):
    # The captain may mark a team complete before the roster is full, as long as a lineup type is
    # set — there is no minimum-member gate.
    cap = await make_user(client, "Cap", "+15555553015")
    team = await make_team(client, cap["id"], sport="soccer")
    gt = await a_game_type(db_session, sport="soccer")  # 5v5, but roster is just the captain
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(gt.id), "completed": True},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["completed"] is True


async def test_admin_cannot_set_lineup_type_or_complete(client, db_session):
    cap = await make_user(client, "Cap", "+15555553017")
    admin = await make_user(client, "Adm", "+15555553018")
    team = await make_team(client, cap["id"], sport="soccer")
    await add_member(db_session, team["id"], admin["id"], role="admin")
    gt = await a_game_type(db_session, sport="soccer")

    lineup = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(gt.id)},
        headers=auth_header(admin["id"]),
    )
    assert lineup.status_code == 403

    # Admin can still edit ordinary fields (proves it's the field, not the whole call, that's gated).
    ok = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"city": "Rabat"},
        headers=auth_header(admin["id"]),
    )
    assert ok.status_code == 200

    complete = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"completed": True},
        headers=auth_header(admin["id"]),
    )
    assert complete.status_code == 403


async def test_completes_once_lineup_and_roster_both_satisfied(client, db_session):
    cap = await make_user(client, "Cap", "+15555553016")
    team = await make_team(client, cap["id"], sport="soccer")
    gt = await a_game_type(db_session, sport="soccer")
    for i in range(gt.players_per_side - 1):
        member = await make_user(client, f"P{i}", f"+1555555400{i}")
        await add_member(db_session, team["id"], member["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(gt.id), "completed": True},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["completed"] is True


async def test_uncompleting_never_needs_validation(client, db_session):
    cap = await make_user(client, "Cap", "+15555553020")
    team = await completed_team(client, db_session, cap, "Kickers")
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}", json={"completed": False}, headers=auth_header(cap["id"])
    )
    assert resp.status_code == 200 and resp.json()["completed"] is False


async def test_editing_unrelated_field_on_completed_team_does_not_reverify(client, db_session):
    cap = await make_user(client, "Cap", "+15555553021")
    team = await completed_team(client, db_session, cap, "Kickers")
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}", json={"description": "New copy"}, headers=auth_header(cap["id"])
    )
    assert resp.status_code == 200 and resp.json()["completed"] is True


async def test_changing_lineup_on_completed_team_does_not_gate_on_roster(client, db_session):
    # No minimum-member gate: the captain can switch a completed team to a larger format even if
    # the current roster couldn't fill it (unfilled slots just show empty on the lineup).
    cap = await make_user(client, "Cap", "+15555553022")
    team = await completed_team(client, db_session, cap, "Kickers", sport="soccer")  # 5v5, 5 members
    eleven_a_side = await a_game_type(db_session, sport="soccer")
    if eleven_a_side.label == "5v5":
        # a_game_type always returns the first soccer row it finds; force an 11v11 via the DB.
        from app.models.game_type import GameType

        eleven_a_side = GameType(sport="soccer", label="11v11", players_per_side=11)
        db_session.add(eleven_a_side)
        await db_session.commit()
        await db_session.refresh(eleven_a_side)
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}",
        json={"game_type_id": str(eleven_a_side.id)},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["completed"] is True


# --- opponent search inherits the team's lineup, not its own ------------------


async def test_opponent_search_publish_ignores_stray_game_type_id_field(client, db_session):
    """OpponentSearchCreate dropped game_type_id; an extra key in the body is just ignored."""
    cap = await make_user(client, "Cap", "+15555553023")
    team = await completed_team(client, db_session, cap, "Kickers", sport="soccer")
    resp = await client.post(
        f"/api/v1/teams/{team['id']}/opponent-searches",
        json={
            "game_type_id": "00000000-0000-0000-0000-000000000000",  # not a real schema field
            "city": "Casablanca",
            "pitch": "Stade Municipal",
            "date": "2026-09-01",
        },
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["game_type_id"] == team["game_type_id"]


# --- jersey numbers -------------------------------------------------------------


async def test_captain_sets_jersey_number(client):
    cap = await make_user(client, "Cap", "+15555553024")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/jersey-number",
        json={"jersey_number": 10},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["jersey_number"] == 10


async def test_jersey_number_can_be_cleared(client):
    cap = await make_user(client, "Cap", "+15555553025")
    team = await make_team(client, cap["id"])
    await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/jersey-number",
        json={"jersey_number": 7},
        headers=auth_header(cap["id"]),
    )
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/jersey-number",
        json={"jersey_number": None},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 200
    assert resp.json()["jersey_number"] is None


async def test_jersey_number_requires_captain_or_admin(client):
    cap = await make_user(client, "Cap", "+15555553026")
    outsider = await make_user(client, "Out", "+15555553027")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/jersey-number",
        json={"jersey_number": 9},
        headers=auth_header(outsider["id"]),
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("value", [-1, 100])
async def test_jersey_number_out_of_range_rejected(client, value):
    cap = await make_user(client, "Cap", "+15555553028")
    team = await make_team(client, cap["id"])
    resp = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{cap['id']}/jersey-number",
        json={"jersey_number": value},
        headers=auth_header(cap["id"]),
    )
    assert resp.status_code == 422
