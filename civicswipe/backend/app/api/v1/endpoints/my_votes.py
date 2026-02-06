"""
My Votes endpoints - user's voting history
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas import MyVotesResponse, MyVoteItem, JurisdictionLevel, MeasureStatus, SwipeResponse, SwipeRequest
from app.models import UserVote, Measure
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()


@router.get("", response_model=MyVotesResponse)
async def get_my_votes(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    level: Optional[JurisdictionLevel] = Query(None),
    outcome: Optional[str] = Query(None, description="Filter by outcome: passed, failed, or pending"),
    topic: Optional[str] = Query(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's voting history with optional filters
    Shows all measures the user has swiped on with pass/fail status
    """
    # Build query joining user_votes with measures
    stmt = select(UserVote, Measure).join(
        Measure, UserVote.measure_id == Measure.id
    ).where(
        UserVote.user_id == current_user.id
    )

    # Apply filters
    if level:
        stmt = stmt.where(Measure.level == level.value)
    if outcome:
        if outcome == "passed":
            stmt = stmt.where(Measure.status == "passed")
        elif outcome == "failed":
            stmt = stmt.where(Measure.status == "failed")
        elif outcome == "pending":
            stmt = stmt.where(Measure.status.notin_(["passed", "failed"]))
    if topic:
        stmt = stmt.where(Measure.topic_tags.contains([topic]))

    # Order by vote date (most recent first)
    stmt = stmt.order_by(UserVote.created_at.desc())
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.fetchall()

    # Build response items
    items = []
    for user_vote, measure in rows:
        # Determine outcome
        outcome_str = None
        outcome_matches = None
        if measure.status == "passed":
            outcome_str = "passed"
            outcome_matches = user_vote.vote == "yes"
        elif measure.status == "failed":
            outcome_str = "failed"
            outcome_matches = user_vote.vote == "no"

        items.append(MyVoteItem(
            measure_id=measure.id,
            title=measure.title,
            summary_short=measure.summary_short,
            level=JurisdictionLevel(measure.level),
            user_vote=user_vote.vote,
            voted_at=user_vote.created_at,
            status=MeasureStatus(measure.status),
            scheduled_for=measure.scheduled_for,
            outcome=outcome_str,
            outcome_matches_user=outcome_matches
        ))

    return MyVotesResponse(
        items=items,
        next_cursor=None  # TODO: Implement cursor pagination
    )


@router.put("/{measure_id}", response_model=SwipeResponse)
async def update_vote(
    measure_id: UUID,
    swipe_data: SwipeRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user's vote on a measure (allows changing vote)
    """
    # Verify measure exists
    measure = await db.get(Measure, measure_id)
    if not measure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measure not found"
        )

    # Get existing vote
    stmt = select(UserVote).where(
        and_(
            UserVote.user_id == current_user.id,
            UserVote.measure_id == measure_id
        )
    )
    result = await db.execute(stmt)
    existing_vote = result.scalar_one_or_none()

    if not existing_vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existing vote found for this measure"
        )

    # Update vote
    existing_vote.vote = swipe_data.vote.value
    await db.commit()
    await db.refresh(existing_vote)

    from app.schemas import UserVote as UserVoteSchema
    return SwipeResponse(
        saved=True,
        user_vote=UserVoteSchema(
            vote=existing_vote.vote,
            created_at=existing_vote.created_at
        )
    )
