from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.models.guest_session import GuestSession

router = APIRouter(prefix="/guest", tags=["guest"])


class GuestSessionResponse(BaseModel):
    """Response model for guest session."""
    session_token: str


@router.post("/sessions", response_model=GuestSessionResponse)
async def create_guest_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create a new guest session.
    Returns a unique session token that can be used to access projects."""
    from starlette.datastructures import MutableHeaders

    # Get client info if available
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create new guest session
    guest_session = GuestSession(
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(guest_session)
    await db.commit()
    await db.refresh(guest_session)

    return {"session_token": guest_session.session_token}


@router.get("/sessions/{session_token}")
async def get_guest_session(
    session_token: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Check if a guest session exists and is valid."""
    result = await db.execute(
        select(GuestSession).where(GuestSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest session not found"
        )

    # Update last activity
    from sqlalchemy import update
    await db.execute(
        update(GuestSession)
        .where(GuestSession.session_token == session_token)
        .values(last_activity=func.now())
    )
    await db.commit()

    return {"valid": True, "session_token": session_token}
