from fastapi import APIRouter

from app.api.v1.endpoints import health, teams, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(teams.router, prefix="/teams", tags=["teams"])

# Register future resource routers here (listings/search, matches, feedback, credits, ...).
