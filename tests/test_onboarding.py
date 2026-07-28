"""The post-signup onboarding wizard's backing endpoints: incremental saves via PATCH /users/me,
and the completion flag via POST /users/me/onboarding/complete."""

import pytest

from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio

SIGNUP = "/api/v1/auth/signup"
PATCH_ME = "/api/v1/users/me"
COMPLETE = "/api/v1/users/me/onboarding/complete"


async def signup(client, **overrides) -> dict:
    creds = {
        "name": "Nadia",
        "email": "nadia@example.com",
        "phone": "+15555552000",
        "password": "hunter2hunter2",
    }
    resp = await client.post(SIGNUP, json={**creds, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_new_signup_defaults_country_and_not_onboarded(client):
    body = await signup(client)
    user = body["user"]
    assert user["onboarding_completed"] is False
    assert user["country"] == "Morocco"
    assert user["favorite_sports"] == []
    assert user["nickname"] is None
    assert user["gender"] is None
    assert user["locale"] == "en"
    assert user["speed_rating"] is None


async def test_patch_me_saves_onboarding_fields_incrementally(client):
    body = await signup(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    step1 = await client.patch(
        PATCH_ME, json={"nickname": "Naz", "age": 27, "gender": "female"}, headers=headers
    )
    assert step1.status_code == 200
    assert step1.json()["nickname"] == "Naz"
    assert step1.json()["age"] == 27
    assert step1.json()["gender"] == "female"
    # still false — PATCH alone never flips the flag
    assert step1.json()["onboarding_completed"] is False

    step2 = await client.patch(
        PATCH_ME, json={"country": "Spain", "city": "Madrid"}, headers=headers
    )
    assert step2.status_code == 200
    assert step2.json()["city"] == "Madrid"
    assert step2.json()["country"] == "Spain"
    # step 1's fields must survive step 2's partial update
    assert step2.json()["nickname"] == "Naz"

    step3 = await client.patch(
        PATCH_ME, json={"favorite_sports": ["soccer", "paddle", "basketball"]}, headers=headers
    )
    assert step3.status_code == 200
    assert set(step3.json()["favorite_sports"]) == {"soccer", "paddle", "basketball"}

    step4 = await client.patch(
        PATCH_ME,
        json={"speed_rating": 4, "strength_rating": 3, "stamina_rating": 5, "agility_rating": 2},
        headers=headers,
    )
    assert step4.status_code == 200
    assert step4.json()["speed_rating"] == 4
    assert step4.json()["agility_rating"] == 2


async def test_complete_onboarding_flips_the_flag(client):
    body = await signup(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = await client.post(COMPLETE, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["onboarding_completed"] is True


async def test_complete_onboarding_requires_auth(client):
    resp = await client.post(COMPLETE)
    assert resp.status_code == 401


async def test_complete_onboarding_does_not_require_fields_filled(client):
    """The endpoint trusts the wizard's client-side gating; it doesn't itself demand a full profile."""
    body = await signup(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = await client.post(COMPLETE, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["nickname"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", 5),  # below MIN_AGE
        ("age", 150),  # above MAX_AGE
        ("speed_rating", 0),  # below MIN_RATING
        ("speed_rating", 6),  # above MAX_RATING
        ("nickname", ""),  # below min_length
        ("favorite_sports", ["not-a-sport"]),
        ("gender", "other"),  # not a Gender member
        ("locale", "de"),  # not a Locale member
    ],
)
async def test_patch_me_validates_onboarding_fields(client, field, value):
    body = await signup(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = await client.patch(PATCH_ME, json={field: value}, headers=headers)
    assert resp.status_code == 422, resp.text


async def test_dev_created_user_also_defaults_correctly(client):
    """POST /users (credential-less, dev-only) must get the same onboarding defaults as signup."""
    resp = await client.post(
        "/api/v1/users", json={"name": "Dev User", "phone": "+15555552099", "email": "dev@example.com"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["country"] == "Morocco"
    assert body["onboarding_completed"] is False


async def test_stub_auth_still_reaches_onboarding_endpoints(client):
    user = await signup(client, email="stub@example.com", phone="+15555552001")
    resp = await client.patch(
        PATCH_ME, json={"nickname": "Stubbed"}, headers=auth_header(user["user"]["id"])
    )
    assert resp.status_code == 200
    assert resp.json()["nickname"] == "Stubbed"
