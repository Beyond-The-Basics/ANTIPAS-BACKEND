# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend for the **Kickoff App** — a sports matchmaking service (soccer/tennis/paddle) that pairs
players and teams for games. The full product spec, data model, and tech-stack rationale live in the
**sibling repo** `../ANTIPAS` (`SPEC.md`, `DATA_MODEL.md`, `TECH_STACK.md`). Treat those as the source of
truth for domain decisions; this repo implements them.

## Commands

Uses `uv` for dependency/venv management. Prefix Python commands with `uv run`.

A `Makefile` wraps all of these; run `make help` for the list. Key one-shot:
`make test-instance` = install + .env + infra + wait-for-db + migrate + seed + serve — a fully
ready-for-testing instance.

```bash
uv sync                       # install deps into .venv from uv.lock
docker compose up -d postgres redis   # local Postgres + Redis (needed for the API/migrations/worker)
uv run alembic upgrade head           # apply migrations
uv run python -m app.db.seed          # seed reference data (game type catalog); idempotent
uv run uvicorn app.main:app --reload  # run API at http://localhost:8000 (docs at /docs, admin at /admin)

uv run pytest                 # run all tests
uv run pytest tests/test_health.py::test_health   # run a single test
uv run ruff check ./app       # lint (app/ only — CI doesn't gate tests/ on lint/format)
uv run ruff check . --fix     # lint + autofix (whole repo, including tests/)

# Full stack (API + worker + beat + postgres + redis) in containers:
docker compose up --build

# Migrations
uv run alembic revision --autogenerate -m "message"   # generate (requires a running Postgres)
uv run alembic downgrade -1                            # roll back one

# Celery (if not using docker compose)
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
uv run celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

## Architecture

FastAPI + async SQLAlchemy 2.0 + PostgreSQL, with Celery/Redis for background jobs and SQLAdmin for
internal moderation tooling.

- `app/main.py` — FastAPI app factory; mounts the versioned API router and the SQLAdmin UI.
- `app/core/config.py` — `Settings` (pydantic-settings), loaded from `.env`. Import the `settings`
  singleton; don't read env vars directly.
- `app/db/` — `base_class.py` defines the declarative `Base` plus `UUIDPKMixin`/`TimestampMixin`
  (all tables use UUID PKs and a `created_at`). `session.py` holds the async engine + `get_db` FastAPI
  dependency.
- `app/models/` — SQLAlchemy models, one file per domain area. **All models must be imported in
  `app/models/__init__.py`** — Alembic autogenerate and SQLAdmin both discover tables via
  `Base.metadata`, so a model missing from that file silently won't get a migration. All status/enum
  columns use `StrEnum`s from `app/models/enums.py` mapped via the `str_enum()` helper there — it stores
  the enum *value* (e.g. `"soccer"`) as a VARCHAR, not the member name, and uses no native Postgres enum
  type. Always use `str_enum(SomeEnum)` for enum columns rather than SQLAlchemy's bare `Enum(...)`.
- `app/db/seed.py` — idempotent reference-data seeding (the `GameType` catalog). Run via
  `python -m app.db.seed` / `make seed` after migrating.
- `app/api/v1/` — `router.py` aggregates endpoint routers under the `/api/v1` prefix (set in settings).
  Add new resource routers there. Endpoints stay thin; domain logic lives in `app/services/`.
- `app/api/deps.py` — shared FastAPI dependencies. **`get_current_user` is the single auth seam.** It is
  currently `get_current_user_stub` (trusts an `X-User-Id` header) so authorization logic can be built
  without a Firebase project. `get_current_user_via_firebase` is written and ready; swap the alias at the
  bottom of the file to go live — route signatures don't change.
- `app/core/firebase.py` — lazy Firebase Admin init + `verify_id_token`. Phone/OTP happens on the mobile
  client; the backend only verifies the ID token. Needs `FIREBASE_CREDENTIALS_PATH` (service-account JSON).
- `app/core/resend.py` — the transactional-email provider client, same shape as `firebase.py`. **Nothing
  above it imports Resend**: domain code depends on the `EmailService` protocol in
  `app/services/email_service.py`, which falls back to a console stub when `RESEND_API_KEY` is unset, so
  dev and tests never hit the network. Swapping providers means a new client + a new `EmailService`.
- `app/schemas/` — Pydantic request/response models (`*Create`/`*Update`/`*Read`); `Read` models use
  `ConfigDict(from_attributes=True)`.
- `app/services/` — business-logic layer. `team_service.py` (team/membership rules),
  `roster_service.py` (RosterSearch + RosterApplication invite/apply/accept → membership),
  `opponent_service.py` (OpponentSearch + OpponentApplication; confirming an application creates a
  `Match`, auto-declines the rest, and closes the search), `match_service.py` (match read/cancel/mark-
  played), `availability_service.py` (PlayerAvailability broadcast — free), `guest_service.py`
  (GuestSearch + GuestApplication; confirming creates a `MatchGuestParticipant`, not a membership —
  one-off substitute for a confirmed Match), `email_verification_service.py` (the 6-digit email OTP:
  one live code per user, 10-minute expiry, 5-attempt cap, 60s resend floor — see below), and
  `credit_service.py` (**stub** `charge_publish` — the real `CreditTransaction` ledger is a later PR).
  Keep endpoints thin; new domain logic goes here.
- `app/services/email_templates.py` — the only user-facing copy rendered server-side, localized to
  `User.locale` across the three locales the product ships. An email has no client around it to
  translate it, so new email copy must land in English, French **and** Darija together.
- `app/workers/` — `celery_app.py` (Celery instance + beat schedule) and `tasks.py`. The beat schedule
  runs `expire_stale_listings` every 10 min; expiring listings and the non-engagement credit refund are
  stubbed and need implementing against the four listing tables.
- `migrations/` — Alembic (async template). `env.py` pulls the DB URL from `settings` and imports
  `app.models.Base` for autogenerate; `alembic.ini`'s `sqlalchemy.url` is intentionally blank.

## Domain notes that affect the schema

These are settled product decisions (see `../ANTIPAS/DATA_MODEL.md`) that aren't obvious from the code:

- **Four separate listing tables, not one generic table**: `RosterSearch` (permanent recruiting,
  stays open across multiple hires), `OpponentSearch` (team-vs-team, requires `team.completed`),
  `GuestSearch` (one-off substitute, attached to a confirmed `Match`, free), `PlayerAvailability`
  (individual broadcast, free). Kept distinct on purpose.
- **Credits are personal, never team-pooled**: `CreditTransaction` always references a `User`.
  Only `OpponentSearch`/`RosterSearch` are charged; `GuestSearch`/`PlayerAvailability` are free.
- **Confirming one `OpponentApplication` creates a `Match`, auto-declines the rest, closes the search**
  (one match per search).
- **Feedback/Report/Dispute polymorphism**: `Feedback` and `Report` reference parties via a
  `(type, id)` pair (`PartyType` = user or team) rather than FKs, because a party can be either.
- **Ad-hoc doubles pairs reuse `Team`** (`is_adhoc=True`, 2 members) rather than a new entity.
- **Adding members is mutual-consent** via the `RosterApplication` invite/accept flow (a listings/search
  milestone, not yet built). The team membership endpoints only manage *existing* memberships (roles,
  transfer, leave, remove); creating a team makes the creator its captain.
- **One live email-verification code per user**, enforced by the unique `user_id` on
  `email_verifications` rather than by convention — requesting a code deletes the previous row. A
  6-digit code is only a million values, so safety comes from the policy (10-min expiry, 5-attempt
  cap, 60s resend floor, bcrypt-hashed storage), not the code. The resend floor is read off the live
  row's `created_at` instead of Redis, so the limit shares a transaction with what it guards. Codes
  are sent best-effort on signup and email change: the account write is committed first, because a
  down mail provider must never roll back a successful registration.

## Tests

`tests/conftest.py` runs integration tests against a dedicated `antipas_test` Postgres DB (models use
Postgres-only types, so SQLite isn't an option); it creates/drops the schema per test and **skips** if
Postgres is unreachable, so `pytest` stays green offline. `make test` brings up Postgres, ensures the test
DB exists, then runs the suite; `make test-quick` runs pytest alone. Tests use the stub auth via the
`auth_header(user_id)` helper (sends `X-User-Id`).
