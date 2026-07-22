# Session notes — 2026-07-22 (ANTIPAS-BACKEND)

Portable summary of the working session, so it can be picked up from another computer.
To resume elsewhere: `git pull`, read this file, and paste the relevant parts into a new
Claude Code session to re-prime context.

## What this project is

Backend for the **Kickoff App** (ANTIPAS) — a sports matchmaking service (soccer / tennis / paddle)
pairing players and teams for games. Product/data-model/tech-stack specs live in the sibling repo
`../ANTIPAS` (`SPEC.md`, `DATA_MODEL.md`, `TECH_STACK.md`) — source of truth for domain decisions.

Stack: FastAPI + async SQLAlchemy 2.0 + PostgreSQL, Alembic (async), Celery + Redis, SQLAdmin at
`/admin`. Package manager `uv`. Auth is a **stub** (`X-User-Id` header) with a ready-to-swap Firebase
path in `app/api/deps.py`.

## Established working conventions

- **Every new feature = GitHub issue → feature branch → pull request.** No direct commits to `main`.
- **Never add the `Co-Authored-By: Claude` trailer** to commit messages in this repo.
- Repo-local git identity: `Mohamed-Moumni` / `mohamedmoumni593@gmail.com`.
- Run `ruff format .` after writing files; keep line length ≤ 110.
- Enum columns use `str_enum()` (stores the enum *value*, not the member name).
- All models must be registered in `app/models/__init__.py` (Alembic + SQLAdmin discovery).
- Tests run against a dedicated `antipas_test` Postgres DB; they **skip** if Postgres is unreachable.

## The four listing types (domain core)

| Listing | Purpose | Charged? |
|---|---|---|
| `RosterSearch` | Permanent team recruiting (stays open across hires) | Yes |
| `OpponentSearch` | Team-vs-team (requires `team.completed`); confirming creates a `Match`, auto-declines the rest, closes the search | Yes |
| `PlayerAvailability` | Individual broadcast | Free |
| `GuestSearch` | One-off substitute attached to a **confirmed** `Match`; confirming creates a `MatchGuestParticipant` (NOT a membership) | Free |

Credits are personal, never team-pooled.

## Progress / PR history

- PR #2 — RosterSearch + RosterApplication (merged)
- PR #4 — OpponentSearch + OpponentApplication + Match, Flow 2 (merged)
- PR #6 — PlayerAvailability (merged)
- **PR #8 — GuestSearch + GuestApplication + MatchGuestParticipant, Flow 1 (OPEN)**
  https://github.com/Beyond-The-Basics/ANTIPAS-BACKEND/pull/8
  Branch `feat/guest-search`, commit `05966b8`. Closes issue #7.
  This effectively completes the "finish the four listing types" milestone once merged.

### GuestSearch feature (this session's work)

Files added/changed:
- `app/schemas/guest.py` — GuestSearchCreate/Read, GuestInviteCreate, GuestApplicationRead, MatchGuestParticipantRead
- `app/services/guest_service.py` — publish/list/withdraw search; apply/invite/accept/decline/withdraw
  application; accept → `MatchGuestParticipant` (+ closes search, auto-declines other pending apps)
- `app/api/v1/endpoints/guest.py` — 12 routes
- `tests/test_guest.py` — 8 integration tests (all passing)
- `app/api/v1/router.py`, `CLAUDE.md` — wired in / documented

Last verified: 8 guest tests pass; full suite 70 passed; lint + format clean.

## Web test client

`../ANTIPAS-WEB` — Vite + React + TypeScript. Dev proxy `/api` → `http://localhost:8000`.
"Act as user" switcher drives the `X-User-Id` header.

## Known backend gaps the web console works around

- No `GET /game-types` endpoint (opponent search needs a manually pasted `game_type_id`).
- Browse endpoints only return **open** listings.

## Remaining roadmap (not yet started)

- Enabling endpoints: `GET /game-types`, team-scoped search listings
- Feedback / Dispute / Report
- Real Credits ledger (`CreditTransaction`) — currently `charge_publish` is a stub
- Background jobs: listing expiry + non-engagement credit refund (`expire_stale_listings` stub)
- Firebase go-live swap (flip the alias in `app/api/deps.py`)
- Notifications, file storage

## Immediate next step

Verify PR #8 CI is green, then merge. After that the four-listing-type milestone is complete;
await direction on which roadmap item to pick up next.
