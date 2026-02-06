"""
Dashboard endpoints - user activity summary
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.schemas import DashboardResponse, DashboardStats, RecentActivity, JurisdictionLevel
from app.models import UserVote, Measure
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's activity dashboard with summary stats
    """
    # Get all user votes with measures
    stmt = select(UserVote, Measure).join(
        Measure, UserVote.measure_id == Measure.id
    ).where(
        UserVote.user_id == current_user.id
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    # Calculate stats
    total_votes = 0
    yea_votes = 0
    nay_votes = 0
    skipped = 0
    measures_passed = 0
    measures_failed = 0
    measures_pending = 0
    alignment_matches = 0
    alignment_total = 0

    recent_activity = []

    for user_vote, measure in rows:
        total_votes += 1

        if user_vote.vote == "yes":
            yea_votes += 1
        elif user_vote.vote == "no":
            nay_votes += 1
        elif user_vote.vote == "skip":
            skipped += 1

        # Check outcome
        if measure.status == "passed":
            measures_passed += 1
            alignment_total += 1
            if user_vote.vote == "yes":
                alignment_matches += 1
        elif measure.status == "failed":
            measures_failed += 1
            alignment_total += 1
            if user_vote.vote == "no":
                alignment_matches += 1
        else:
            measures_pending += 1

        # Add to recent activity (we'll sort and limit later)
        recent_activity.append({
            "measure_id": measure.id,
            "title": measure.title,
            "level": measure.level,
            "user_vote": user_vote.vote,
            "voted_at": user_vote.created_at,
            "outcome": measure.status if measure.status in ["passed", "failed"] else None
        })

    # Sort by most recent and limit to 5
    recent_activity.sort(key=lambda x: x["voted_at"], reverse=True)
    recent_activity = recent_activity[:5]

    # Calculate alignment score
    alignment_score = None
    if alignment_total > 0:
        alignment_score = round((alignment_matches / alignment_total) * 100, 1)

    return DashboardResponse(
        stats=DashboardStats(
            total_votes=total_votes,
            yea_votes=yea_votes,
            nay_votes=nay_votes,
            skipped=skipped,
            measures_passed=measures_passed,
            measures_failed=measures_failed,
            measures_pending=measures_pending,
            alignment_score=alignment_score
        ),
        recent_activity=[
            RecentActivity(
                measure_id=item["measure_id"],
                title=item["title"],
                level=JurisdictionLevel(item["level"]),
                user_vote=item["user_vote"],
                voted_at=item["voted_at"],
                outcome=item["outcome"]
            )
            for item in recent_activity
        ]
    )
