"""
Matching endpoints - compare user votes to official votes
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas import (
    MatchesResponse, MatchSummary, MatchDetail,
    JurisdictionLevel, MeasureStatus, VoteValue
)
from app.models import MatchResult, Measure, UserVote, VoteEvent
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()


@router.get("", response_model=MatchesResponse)
async def get_matches(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    level: Optional[JurisdictionLevel] = Query(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get measures where user voted and official results are available
    Shows match scores between user and their officials
    """
    # Query match results with measure and user vote
    stmt = select(MatchResult, Measure, UserVote).join(
        Measure, MatchResult.measure_id == Measure.id
    ).join(
        UserVote, and_(
            UserVote.user_id == MatchResult.user_id,
            UserVote.measure_id == MatchResult.measure_id
        )
    ).where(
        MatchResult.user_id == current_user.id
    )
    
    # Apply filters
    if level:
        stmt = stmt.where(Measure.level == level.value)
    
    # Order by computed date (most recent first)
    stmt = stmt.order_by(MatchResult.computed_at.desc())
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    # Build response items
    items = []
    for match_result, measure, user_vote in rows:
        items.append(MatchSummary(
            measure_id=measure.id,
            title=measure.title,
            level=JurisdictionLevel(measure.level),
            user_vote=VoteValue(user_vote.vote),
            outcome=MeasureStatus(measure.status),
            match_score=float(match_result.match_score),
            computed_at=match_result.computed_at
        ))
    
    return MatchesResponse(
        items=items,
        next_cursor=None  # TODO: Implement cursor pagination
    )


@router.get("/{measure_id}", response_model=MatchDetail)
async def get_match_detail(
    measure_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed match breakdown for a specific measure
    Shows how each official voted and whether it matched the user
    """
    # Get match result
    match_result = await db.get(
        MatchResult,
        {"user_id": current_user.id, "measure_id": measure_id}
    )
    
    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found. Official votes may not be available yet."
        )
    
    # Get measure
    measure = await db.get(Measure, measure_id)
    if not measure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measure not found"
        )
    
    # Get user vote
    stmt = select(UserVote).where(
        and_(
            UserVote.user_id == current_user.id,
            UserVote.measure_id == measure_id
        )
    )
    result = await db.execute(stmt)
    user_vote = result.scalar_one_or_none()
    
    if not user_vote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User vote not found"
        )
    
    # Get vote event
    stmt = select(VoteEvent).where(VoteEvent.measure_id == measure_id)
    result = await db.execute(stmt)
    vote_event = result.scalar_one_or_none()
    
    if not vote_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vote event not found"
        )
    
    return MatchDetail(
        measure_id=measure.id,
        title=measure.title,
        level=JurisdictionLevel(measure.level),
        user_vote=VoteValue(user_vote.vote),
        vote_event={
            "id": vote_event.id,
            "body": vote_event.body,
            "held_at": vote_event.held_at,
            "result": vote_event.result
        },
        match={
            "match_score": float(match_result.match_score),
            "breakdown": match_result.breakdown
        }
    )
