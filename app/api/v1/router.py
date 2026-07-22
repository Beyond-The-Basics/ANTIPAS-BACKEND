from fastapi import APIRouter

from app.api.v1.endpoints import health, matches, opponent, roster, teams, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
# These routers use absolute paths (they span /teams, /<listing>-searches, /users/me, /matches).
api_router.include_router(roster.router)
api_router.include_router(opponent.router)
api_router.include_router(matches.router)

# Register future resource routers here (guest/availability, feedback, credits, ...).
