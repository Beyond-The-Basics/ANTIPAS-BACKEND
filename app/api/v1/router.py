from fastapi import APIRouter

from app.api.v1.endpoints import health, roster, teams, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])
# roster uses absolute paths (spans /teams, /roster-searches, /roster-applications, /users/me).
api_router.include_router(roster.router)

# Register future resource routers here (opponent/guest/availability, matches, feedback, credits, ...).
