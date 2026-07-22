# Kickoff App backend — common tasks.
# `uv` is expected on PATH (installer puts it in ~/.local/bin); we prepend it just in case.
export PATH := $(HOME)/.local/bin:$(PATH)

UV := uv
COMPOSE := docker compose
CELERY_APP := app.workers.celery_app.celery_app

.DEFAULT_GOAL := help

# ---- meta ----------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---- setup ---------------------------------------------------------------

.PHONY: install
install: ## Install dependencies into .venv from uv.lock
	$(UV) sync

.PHONY: env
env: ## Create .env from .env.example if missing
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

# ---- local infra (postgres + redis) --------------------------------------

.PHONY: infra
infra: ## Start Postgres + Redis in the background
	$(COMPOSE) up -d postgres redis

.PHONY: infra-stop
infra-stop: ## Stop Postgres + Redis (keep data)
	$(COMPOSE) stop postgres redis

# ---- run the app ---------------------------------------------------------

.PHONY: dev
dev: env infra migrate ## One command: env + infra + migrate + reload server
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: test-instance
test-instance: install env infra wait-db migrate seed ## Spin up a fully-ready-for-testing instance and serve it
	@echo ""
	@echo "  Backend ready for testing:"
	@echo "    API   -> http://localhost:8000"
	@echo "    Docs  -> http://localhost:8000/docs"
	@echo "    Admin -> http://localhost:8000/admin"
	@echo ""
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: run
run: ## Run the API server (reload) — assumes infra is already up
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Run the Celery worker
	$(UV) run celery -A $(CELERY_APP) worker --loglevel=info

.PHONY: beat
beat: ## Run the Celery beat scheduler
	$(UV) run celery -A $(CELERY_APP) beat --loglevel=info

# ---- full stack in docker ------------------------------------------------

.PHONY: up
up: ## Build & start the full stack (api + worker + beat + postgres + redis)
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop all containers (keep data)
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop all containers AND delete volumes (drops the database)
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs from all containers
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

# ---- database / migrations ----------------------------------------------

.PHONY: wait-db
wait-db: ## Block until the Postgres container reports healthy
	@echo "waiting for Postgres to be healthy..."
	@until [ "$$($(COMPOSE) ps -q postgres | xargs -r docker inspect -f '{{.State.Health.Status}}')" = "healthy" ]; do \
		sleep 1; \
	done
	@echo "Postgres is healthy."

.PHONY: migrate
migrate: ## Apply all migrations (alembic upgrade head)
	$(UV) run alembic upgrade head

.PHONY: seed
seed: ## Seed reference data (game type catalog); idempotent
	$(UV) run python -m app.db.seed

.PHONY: migration
migration: ## Autogenerate a migration: make migration m="message" (Postgres must be running)
	@test -n "$(m)" || (echo "usage: make migration m=\"your message\"" && exit 1)
	$(UV) run alembic revision --autogenerate -m "$(m)"

.PHONY: downgrade
downgrade: ## Roll back one migration
	$(UV) run alembic downgrade -1

.PHONY: psql
psql: ## Open a psql shell in the Postgres container
	$(COMPOSE) exec postgres psql -U antipas -d antipas

# ---- quality -------------------------------------------------------------

.PHONY: test
test: ## Run the test suite
	$(UV) run pytest -q

.PHONY: lint
lint: ## Lint with ruff
	$(UV) run ruff check .

.PHONY: fmt
fmt: ## Auto-fix lint issues + format with ruff
	$(UV) run ruff check . --fix
	$(UV) run ruff format .

.PHONY: check
check: lint test ## Lint + test (run before committing)
