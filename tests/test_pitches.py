"""The shared venue directory: browsing it by country/city, adding a venue that isn't listed, and
the (name, country, city) identity that keeps the seeder and hand-added venues from duplicating
each other."""

import pytest

from app.db.pitch_catalog import CASABLANCA_PITCHES, CITY, COUNTRY
from app.db.seed import seed_pitches
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def add_pitch(client, user_id, name, city="Casablanca", country="Morocco"):
    return await client.post(
        "/api/v1/pitches",
        json={"name": name, "country": country, "city": city},
        headers=auth_header(user_id),
    )


async def test_anyone_signed_in_can_add_a_pitch(client, db_session):
    user = await make_user(client, "Adder", "+15555555100")

    created = await add_pitch(client, user["id"], "Stade Père Jégo")
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Stade Père Jégo"
    assert body["country"] == "Morocco"
    assert body["city"] == "Casablanca"


async def test_adding_the_same_venue_twice_returns_the_same_row(client, db_session):
    one = await make_user(client, "One", "+15555555101")
    two = await make_user(client, "Two", "+15555555102")

    first = await add_pitch(client, one["id"], "Stade Municipal")
    assert first.status_code == 201

    # A different user, same venue: adopted rather than duplicated, and 200 rather than 201 because
    # nothing was created.
    second = await add_pitch(client, two["id"], "Stade Municipal")
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_matching_is_case_insensitive_and_trims(client, db_session):
    user = await make_user(client, "Caser", "+15555555103")

    seeded = await add_pitch(client, user["id"], "Complexe Sportif Kahrama")
    typed = await add_pitch(client, user["id"], "  complexe sportif kahrama  ")

    assert typed.status_code == 200
    assert typed.json()["id"] == seeded.json()["id"]
    # The original casing wins — a hand-typed lowercase variant must not shadow the directory's.
    assert typed.json()["name"] == "Complexe Sportif Kahrama"


async def test_same_name_in_another_city_is_a_different_venue(client, db_session):
    user = await make_user(client, "Traveller", "+15555555104")

    casa = await add_pitch(client, user["id"], "Stade Municipal", city="Casablanca")
    rabat = await add_pitch(client, user["id"], "Stade Municipal", city="Rabat")

    assert rabat.status_code == 201
    assert rabat.json()["id"] != casa.json()["id"]


async def test_listing_filters_by_city_and_sorts_by_name(client, db_session):
    user = await make_user(client, "Browser", "+15555555105")
    await add_pitch(client, user["id"], "Zenith Park", city="Casablanca")
    await add_pitch(client, user["id"], "Al Amal", city="Casablanca")
    await add_pitch(client, user["id"], "Rabat Only", city="Rabat")

    listed = await client.get(
        "/api/v1/pitches?country=Morocco&city=Casablanca", headers=auth_header(user["id"])
    )
    assert listed.status_code == 200
    names = [p["name"] for p in listed.json()]
    assert names == ["Al Amal", "Zenith Park"]

    empty = await client.get(
        "/api/v1/pitches?country=Morocco&city=Nowhere", headers=auth_header(user["id"])
    )
    assert empty.json() == []


async def test_listing_requires_authentication(client, db_session):
    assert (await client.get("/api/v1/pitches")).status_code == 401


async def test_seed_pitches_is_idempotent(client, db_session):
    user = await make_user(client, "Seeder", "+15555555106")

    assert await seed_pitches(db_session) == len(CASABLANCA_PITCHES)
    # Re-running adds nothing, which is the property that lets `make seed` run on every deploy.
    assert await seed_pitches(db_session) == 0

    listed = await client.get(
        f"/api/v1/pitches?country={COUNTRY}&city={CITY}", headers=auth_header(user["id"])
    )
    assert len(listed.json()) == len(CASABLANCA_PITCHES)


async def test_seeding_adopts_a_hand_added_venue(client, db_session):
    """A captain adds a venue the directory happens to contain, then the seeder runs: one row, not
    two. This is the case `place_id` used to cover before names became the identity."""
    user = await make_user(client, "Early", "+15555555107")
    typed = await add_pitch(client, user["id"], CASABLANCA_PITCHES[0].lower(), city=CITY)

    assert await seed_pitches(db_session) == len(CASABLANCA_PITCHES) - 1

    listed = await client.get(
        f"/api/v1/pitches?country={COUNTRY}&city={CITY}", headers=auth_header(user["id"])
    )
    body = listed.json()
    assert len(body) == len(CASABLANCA_PITCHES)
    assert typed.json()["id"] in {p["id"] for p in body}
