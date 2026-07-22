from fastapi import FastAPI

from app.admin import setup_admin
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title="Kickoff App API", version="0.1.0")

app.include_router(api_router, prefix=settings.api_v1_prefix)

setup_admin(app)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "kickoff-api", "docs": "/docs"}
