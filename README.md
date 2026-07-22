# Kickoff App — Backend

Sports matchmaking API (soccer / tennis / paddle) that pairs players and teams for games.
Product spec and data model live in the sibling `../ANTIPAS` repo.

**Stack:** FastAPI · async SQLAlchemy 2.0 · PostgreSQL · Alembic · Celery + Redis · SQLAdmin ·
Firebase Auth (phone/OTP). Managed with [uv](https://docs.astral.sh/uv/).

## Quick start

```bash
uv sync                                  # install dependencies
cp .env.example .env                     # defaults match docker-compose
docker compose up -d postgres redis      # local infra
uv run alembic upgrade head              # create the schema
uv run uvicorn app.main:app --reload     # http://localhost:8000
```

- API docs (OpenAPI): http://localhost:8000/docs
- Admin UI: http://localhost:8000/admin

Or run the whole stack (API + Celery worker + beat + Postgres + Redis) in containers:

```bash
docker compose up --build
```

## Development

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run alembic revision --autogenerate -m "..."   # new migration (Postgres must be running)
```

## Layout

```
app/
  core/       settings
  db/         engine, session, declarative Base + mixins
  models/     SQLAlchemy models (register every model in models/__init__.py)
  schemas/    Pydantic request/response models
  api/v1/     versioned routers + endpoints
  services/   business logic
  workers/    Celery app + tasks
migrations/   Alembic
tests/
```
