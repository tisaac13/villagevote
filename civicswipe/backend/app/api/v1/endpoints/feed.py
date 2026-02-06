"""
Feed endpoints - personalized swipe feed
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.schemas import FeedResponse, FeedCard, MeasureDetail, JurisdictionLevel, MeasureStatus
from app.models import Measure, UserDivision, UserVote, MeasureSource, MeasureStatusEvent, VoteEvent
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()


# Main categories for voting - mapped from detailed topic tags
CATEGORY_MAPPING = {
    "Budget & Economy": ["Budget", "Economy", "Taxes", "Banking", "Government Spending", "Economic Development"],
    "Immigration": ["Immigration", "Asylum"],
    "Healthcare": ["Healthcare", "Medicaid", "Mental Health", "Public Health"],
    "Education": ["Education", "School Choice"],
    "Environment": ["Environment", "Energy", "Agriculture"],
    "Public Safety": ["Public Safety", "Crime", "Law Enforcement", "Drug Policy"],
    "Civil Rights": ["Civil Rights", "Women's Issues", "Fair Housing"],
    "Foreign Policy": ["International Affairs"],
    "Infrastructure": ["Infrastructure", "Transportation", "Public Utilities", "Utilities"],
    "Veterans & Military": ["Veterans", "World War II"],
    "Government": ["Congress", "Government", "Government Operations", "Government Oversight", "Government Transparency"],
    "Housing": ["Housing", "Land Use", "Zoning", "Property Rights"],
    "Labor & Business": ["Labor", "Business", "Government Contracting"],
    "Elections": ["Elections", "Civic Engagement"],
}


@router.get("/categories", response_model=List[dict])
async def get_categories(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available voting categories with bill counts"""
    categories = []

    for category_name, topics in CATEGORY_MAPPING.items():
        # Count bills in this category
        count_stmt = select(func.count(Measure.id)).where(
            Measure.level == "federal",
            Measure.topic_tags.overlap(topics)
        )
        result = await db.execute(count_stmt)
        count = result.scalar() or 0

        if count > 0:
            categories.append({
                "name": category_name,
                "topics": topics,
                "count": count,
                "icon": get_category_icon(category_name)
            })

    # Sort by count descending
    categories.sort(key=lambda x: x["count"], reverse=True)
    return categories


def get_category_icon(category: str) -> str:
    """Get emoji icon for category"""
    icons = {
        "Budget & Economy": "💰",
        "Immigration": "🌎",
        "Healthcare": "🏥",
        "Education": "📚",
        "Environment": "🌿",
        "Public Safety": "🛡️",
        "Civil Rights": "⚖️",
        "Foreign Policy": "🌐",
        "Infrastructure": "🏗️",
        "Veterans & Military": "🎖️",
        "Government": "🏛️",
        "Housing": "🏠",
        "Labor & Business": "💼",
        "Elections": "🗳️",
    }
    return icons.get(category, "📋")


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    level: Optional[JurisdictionLevel] = Query(None),
    status: Optional[MeasureStatus] = Query(None),  # None means show all statuses
    topic: Optional[str] = Query(None),
    include_skipped: bool = Query(True, description="Include previously skipped items at end"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized swipe feed
    Returns measures relevant to user's divisions, ranked by scheduled date
    Skipped items are recycled to the end of the feed
    """
    # Get user's divisions
    stmt = select(UserDivision.division_id).where(UserDivision.user_id == current_user.id)
    result = await db.execute(stmt)
    user_division_ids = [row[0] for row in result.fetchall()]

    # Get IDs of measures user has already voted on (yes/no, not skip)
    voted_stmt = select(UserVote.measure_id, UserVote.vote).where(
        UserVote.user_id == current_user.id
    )
    voted_result = await db.execute(voted_stmt)
    user_votes = {row[0]: row[1] for row in voted_result.fetchall()}

    voted_yes_no_ids = [mid for mid, vote in user_votes.items() if vote in ("yes", "no")]
    skipped_ids = [mid for mid, vote in user_votes.items() if vote == "skip"]

    # Build base query - Currently focused on federal legislation only (House & Senate)
    # City/local legislation will be added when we have enough users in relevant areas
    base_stmt = select(Measure).where(Measure.level == "federal")

    # Filter out procedural items
    base_stmt = base_stmt.where(Measure.summary_short != "Procedural item - no action needed from voters.")

    # Apply filters
    if level:
        base_stmt = base_stmt.where(Measure.level == level.value)
    if status:
        base_stmt = base_stmt.where(Measure.status == status.value)
    if topic:
        base_stmt = base_stmt.where(Measure.topic_tags.contains([topic]))

    # First: Get unvoted measures (priority)
    unvoted_stmt = base_stmt.where(~Measure.id.in_(list(user_votes.keys()))) if user_votes else base_stmt
    unvoted_stmt = unvoted_stmt.order_by(Measure.scheduled_for.asc().nullslast(), Measure.updated_at.desc())
    unvoted_stmt = unvoted_stmt.limit(limit)

    result = await db.execute(unvoted_stmt)
    unvoted_measures = list(result.scalars().all())

    # Second: If we have room and include_skipped is True, add skipped measures
    skipped_measures = []
    if include_skipped and len(unvoted_measures) < limit and skipped_ids:
        remaining = limit - len(unvoted_measures)
        skipped_stmt = base_stmt.where(Measure.id.in_(skipped_ids))
        skipped_stmt = skipped_stmt.order_by(Measure.scheduled_for.asc().nullslast())
        skipped_stmt = skipped_stmt.limit(remaining)

        result = await db.execute(skipped_stmt)
        skipped_measures = list(result.scalars().all())

    # Combine: unvoted first, then skipped
    all_measures = unvoted_measures + skipped_measures

    # Build feed cards
    items = []
    for measure in all_measures:
        # Get sources
        sources_stmt = select(MeasureSource).where(MeasureSource.measure_id == measure.id)
        sources_result = await db.execute(sources_stmt)
        sources = sources_result.scalars().all()

        # Check if this was previously skipped
        was_skipped = measure.id in skipped_ids

        items.append(FeedCard(
            measure_id=measure.id,
            title=measure.title,
            level=JurisdictionLevel(measure.level),
            jurisdiction_name=f"Level: {measure.level}",
            status=MeasureStatus(measure.status),
            scheduled_for=measure.scheduled_for,
            topic_tags=measure.topic_tags or [],
            summary_short=measure.summary_short,
            sources=[
                {"label": s.label, "url": s.url, "ctype": s.ctype}
                for s in sources
            ],
            user_vote="skip" if was_skipped else None,
            external_id=measure.external_id
        ))

    return FeedResponse(items=items, next_cursor=None)


@router.get("/measures/{measure_id}", response_model=MeasureDetail)
async def get_measure_detail(
    measure_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific measure"""
    measure = await db.get(Measure, measure_id)
    if not measure:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measure not found")
    
    # Get sources
    sources_stmt = select(MeasureSource).where(MeasureSource.measure_id == measure_id)
    sources_result = await db.execute(sources_stmt)
    sources = sources_result.scalars().all()
    
    # Get timeline
    timeline_stmt = select(MeasureStatusEvent).where(
        MeasureStatusEvent.measure_id == measure_id
    ).order_by(MeasureStatusEvent.effective_at.asc())
    timeline_result = await db.execute(timeline_stmt)
    timeline = timeline_result.scalars().all()
    
    # Get vote events
    events_stmt = select(VoteEvent).where(VoteEvent.measure_id == measure_id)
    events_result = await db.execute(events_stmt)
    vote_events = events_result.scalars().all()
    
    # Get user vote
    vote_stmt = select(UserVote).where(
        and_(UserVote.user_id == current_user.id, UserVote.measure_id == measure_id)
    )
    vote_result = await db.execute(vote_stmt)
    user_vote = vote_result.scalar_one_or_none()
    
    return MeasureDetail(
        measure={
            "id": measure.id,
            "title": measure.title,
            "level": measure.level,
            "status": measure.status,
            "introduced_at": measure.introduced_at,
            "scheduled_for": measure.scheduled_for,
            "summary_short": measure.summary_short,
            "summary_long": measure.summary_long
        },
        sources=[{"label": s.label, "url": s.url, "ctype": s.ctype, "is_primary": s.is_primary} for s in sources],
        timeline=[{"status": t.status, "effective_at": t.effective_at} for t in timeline],
        vote_events=[
            {
                "id": ve.id,
                "body": ve.body,
                "scheduled_for": ve.scheduled_for,
                "held_at": ve.held_at,
                "result": ve.result
            }
            for ve in vote_events
        ],
        user_vote={"vote": user_vote.vote, "created_at": user_vote.created_at} if user_vote else None
    )
