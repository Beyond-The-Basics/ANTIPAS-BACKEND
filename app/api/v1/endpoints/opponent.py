import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import Sport
from app.models.search import OpponentApplication
from app.models.user import User
from app.realtime import hub
from app.schemas.match import MatchRead
from app.schemas.opponent import (
    NegotiationMessageCreate,
    NegotiationMessageRead,
    NegotiationProposalRead,
    OpponentApplicationCreate,
    OpponentApplicationRead,
    OpponentSearchCreate,
    OpponentSearchRead,
    ProposeTerms,
)
from app.services import opponent_service, team_service

router = APIRouter(tags=["opponent"])

# --- OpponentSearch -----------------------------------------------------------


@router.post(
    "/teams/{team_id}/opponent-searches",
    response_model=OpponentSearchRead,
    status_code=status.HTTP_201_CREATED,
)
async def publish_opponent_search(
    team_id: uuid.UUID,
    data: OpponentSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await opponent_service.publish_opponent_search(db, team, current_user, data)


@router.get("/opponent-searches", response_model=list[OpponentSearchRead])
async def browse_opponent_searches(
    city: str | None = None,
    sport: Sport | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    return await opponent_service.list_opponent_searches(db, city, sport, limit, offset)


@router.get("/opponent-searches/{search_id}", response_model=OpponentSearchRead)
async def get_opponent_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await opponent_service.get_search_or_404(db, search_id)


@router.post("/opponent-searches/{search_id}/withdraw", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_opponent_search(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    await opponent_service.withdraw_opponent_search(db, search, current_user)


# --- OpponentApplication ------------------------------------------------------


@router.post(
    "/opponent-searches/{search_id}/applications",
    response_model=OpponentApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_search(
    search_id: uuid.UUID,
    data: OpponentApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    return await opponent_service.apply_to_search(db, search, current_user, data.responding_team_id)


@router.get(
    "/opponent-searches/{search_id}/applications",
    response_model=list[OpponentApplicationRead],
)
async def list_search_applications(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search = await opponent_service.get_search_or_404(db, search_id)
    return await opponent_service.list_search_applications(db, search, current_user)


@router.get(
    "/teams/{team_id}/opponent-applications",
    response_model=list[OpponentApplicationRead],
)
async def list_team_applications(
    team_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    team = await team_service.get_team_or_404(db, team_id)
    return await opponent_service.list_team_applications(db, team, current_user)


@router.post(
    "/opponent-applications/{application_id}/withdraw",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def withdraw_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    await opponent_service.withdraw_application(db, application, current_user)


# --- match negotiation (accept challenge -> chat -> propose -> agree) ----------


@router.post("/opponent-applications/{application_id}/accept", response_model=OpponentApplicationRead)
async def accept_challenge(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    application = await opponent_service.accept_challenge(db, application, current_user)
    await hub.broadcast(str(application_id), {"type": "accepted"})
    return application


@router.post("/opponent-applications/{application_id}/propose", response_model=OpponentApplicationRead)
async def propose_terms(
    application_id: uuid.UUID,
    data: ProposeTerms,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    application = await opponent_service.propose_terms(
        db,
        application,
        current_user,
        data.date,
        data.pitch,
        data.booked_by_team_id,
        end_date=data.end_date,
        pitch_address=data.pitch_address,
    )
    await hub.broadcast(
        str(application_id),
        {
            "type": "proposal",
            "proposed_date": application.proposed_date.isoformat() if application.proposed_date else None,
            "proposed_end_date": application.proposed_end_date.isoformat()
            if application.proposed_end_date
            else None,
            "proposed_pitch": application.proposed_pitch,
            "proposed_pitch_address": application.proposed_pitch_address,
            "proposed_by_team_id": str(application.proposed_by_team_id)
            if application.proposed_by_team_id
            else None,
            "proposed_booked_by_team_id": str(application.proposed_booked_by_team_id)
            if application.proposed_booked_by_team_id
            else None,
        },
    )
    return application


@router.post("/opponent-applications/{application_id}/agree", response_model=MatchRead)
async def agree_terms(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    match = await opponent_service.agree(db, application, current_user)
    await hub.broadcast(str(application_id), {"type": "agreed", "match_id": str(match.id)})
    return match


@router.get(
    "/opponent-applications/{application_id}/proposals",
    response_model=list[NegotiationProposalRead],
)
async def list_proposals(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    return await opponent_service.list_proposals(db, application, current_user)


@router.get(
    "/opponent-applications/{application_id}/messages",
    response_model=list[NegotiationMessageRead],
)
async def list_messages(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    return await opponent_service.list_messages(db, application, current_user)


@router.post(
    "/opponent-applications/{application_id}/messages",
    response_model=NegotiationMessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    application_id: uuid.UUID,
    data: NegotiationMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await opponent_service.get_application_or_404(db, application_id)
    message = await opponent_service.post_message(db, application, current_user, data.body)
    await hub.broadcast(
        str(application_id),
        {
            "type": "message",
            "id": str(message.id),
            "sender_user_id": str(message.sender_user_id),
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        },
    )
    return message


@router.websocket("/ws/negotiations/{application_id}")
async def negotiation_ws(
    websocket: WebSocket,
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Real-time chat for a match negotiation. Browsers can't set auth headers on a WebSocket, so
    the acting user id is passed as a query param (matching the stub-auth model)."""
    user = await db.get(User, user_id)
    application = await db.get(OpponentApplication, application_id)
    if user is None or application is None:
        await websocket.close(code=4404)
        return
    try:
        await opponent_service.authorize_negotiation_member(db, application, user)
    except Exception:
        await websocket.close(code=4403)
        return

    room = str(application_id)
    await websocket.accept()
    await hub.join(room, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "message":
                body = (data.get("body") or "").strip()
                if body:
                    message = await opponent_service.post_message(db, application, user, body)
                    await hub.broadcast(
                        room,
                        {
                            "type": "message",
                            "id": str(message.id),
                            "sender_user_id": str(user_id),
                            "body": message.body,
                            "created_at": message.created_at.isoformat(),
                        },
                    )
    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave(room, websocket)
