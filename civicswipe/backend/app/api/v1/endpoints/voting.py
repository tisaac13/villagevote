"""
Voting endpoints - record user votes (swipes)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.cache import cache_delete, reps_key
from app.schemas import SwipeRequest, SwipeResponse, UserVote as UserVoteSchema
from app.models import Measure, UserVote
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()


@router.post("/{measure_id}/swipe", response_model=SwipeResponse)
async def swipe(
    measure_id: UUID,
    swipe_data: SwipeRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Record user vote (swipe) on a measure
    Supports idempotency via Idempotency-Key header
    """
    # Verify measure exists
    measure = await db.get(Measure, measure_id)
    if not measure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measure not found"
        )
    
    # Check if user already voted
    stmt = select(UserVote).where(
        and_(
            UserVote.user_id == current_user.id,
            UserVote.measure_id == measure_id
        )
    )
    result = await db.execute(stmt)
    existing_vote = result.scalar_one_or_none()
    
    if existing_vote:
        # Update existing vote
        existing_vote.vote = swipe_data.vote.value
        await db.commit()
        await db.refresh(existing_vote)

        # Invalidate representatives cache so alignment recomputes
        await cache_delete(reps_key(current_user.id))

        return SwipeResponse(
            saved=True,
            user_vote=UserVoteSchema(
                vote=existing_vote.vote,
                created_at=existing_vote.created_at
            )
        )
    else:
        # Create new vote
        new_vote = UserVote(
            user_id=current_user.id,
            measure_id=measure_id,
            vote=swipe_data.vote.value
        )
        db.add(new_vote)
        await db.commit()
        await db.refresh(new_vote)

        # Invalidate representatives cache so alignment recomputes
        await cache_delete(reps_key(current_user.id))

        return SwipeResponse(
            saved=True,
            user_vote=UserVoteSchema(
                vote=new_vote.vote,
                created_at=new_vote.created_at
            )
        )
