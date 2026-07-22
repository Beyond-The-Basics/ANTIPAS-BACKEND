"""Firebase Admin integration.

Phone/OTP verification happens on the mobile client; the backend only *verifies* the ID token
the client sends. This module lazily initializes the Admin SDK from the service-account JSON at
`settings.firebase_credentials_path` and exposes `verify_id_token`.

Not wired into request handling yet — see `app/api/deps.py`, which currently uses a stub
`get_current_user`. Swap to `get_current_user_via_firebase` there once a service-account JSON is
configured.
"""

from functools import lru_cache
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import settings


@lru_cache
def _get_app() -> firebase_admin.App:
    if not settings.firebase_credentials_path:
        raise RuntimeError("FIREBASE_CREDENTIALS_PATH is not set; cannot initialize Firebase Admin SDK.")
    cred = credentials.Certificate(settings.firebase_credentials_path)
    return firebase_admin.initialize_app(cred)


def verify_id_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return its decoded claims (raises on invalid/expired)."""
    return auth.verify_id_token(token, app=_get_app())
