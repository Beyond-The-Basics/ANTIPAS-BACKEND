import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.user import User
from app.schemas.guest import (
    GuestApplicationRead,
    GuestInviteCreate,
    GuestSearchCreate,
    GuestSearchRead,
    MatchGuestParticipantRead,
)
from app.services import guest_service

router = APIRouter(tags=["guest"])

# --- GuestSearch --------------------------------------------------------------


@router.post(
    "/matches/{match_id}/guest-searches",
    response_model=GuestSearchRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_guest_search(
    match_id: uuid.UUID,
    data: GuestSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await guest_service.publish_guest_search(db, match_id, current_user, data.team_id)


@router.get("/guest-searches", response_model=list[GuestSearchRead])
async def browse_guest_searches(
    city: str | None = None,
    sport: Sport | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await guest_service.list_guest_searches(db, city, sport, limit, offset)


@router.get("/guest-searches/{search_id}", response_model=GuestSearchRead)
async def get_guest_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await guest_service.get_search_or_404(db, search_id)


@router.post("/guest-searches/{search_id}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_guest_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await guest_service.get_search_or_404(db, search_id)
    await guest_service.withdraw_guest_search(db, search, current_user)


# --- GuestApplication ---------------------------------------------------------


@router.post(
    "/guest-searches/{search_id}/applications",
    response_model=GuestApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_guest_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await guest_service.get_search_or_404(db, search_id)
    return await guest_service.apply_to_search(db, search, current_user)


@router.get(
    "/guest-searches/{search_id}/applications",
    response_model=list[GuestApplicationRead],
)
async def list_search_applications(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await guest_service.get_search_or_404(db, search_id)
    return await guest_service.list_search_applications(db, search, current_user)


@router.post(
    "/matches/{match_id}/guest-invitations",
    response_model=GuestApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_guest(
    match_id: uuid.UUID,
    data: GuestInviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await guest_service.invite_guest(db, match_id, current_user, data.team_id, data.user_id)


@router.get("/users/me/guest-applications", response_model=list[GuestApplicationRead])
async def list_my_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await guest_service.list_my_applications(db, current_user)


@router.get("/matches/{match_id}/guests", response_model=list[MatchGuestParticipantRead])
async def list_match_guests(match_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await guest_service.list_match_guests(db, match_id)


@router.post("/guest-applications/{application_id}/accept", response_model=MatchGuestParticipantRead)
async def accept_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await guest_service.get_application_or_404(db, application_id)
    return await guest_service.accept_application(db, application, current_user)


@router.post(
    "/guest-applications/{application_id}/decline",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def decline_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await guest_service.get_application_or_404(db, application_id)
    await guest_service.decline_application(db, application, current_user)


@router.post(
    "/guest-applications/{application_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await guest_service.get_application_or_404(db, application_id)
    await guest_service.withdraw_application(db, application, current_user)
