"""
Dashboard endpoints - user activity summary.

Uses SQL aggregation instead of loading all rows into Python.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_

from app.core.database import get_db
from app.core.cache import cache_get, cache_set, dashboard_key
from app.schemas import DashboardResponse, DashboardStats, RecentActivity, JurisdictionLevel
from app.models import UserVote, Measure
from app.api.v1.endpoints.profile import get_current_user

router = APIRouter()

# Chamber filter expressions for federal measures
_is_federal = Measure.level == "federal"
_is_house = and_(
    _is_federal,
    (
        Measure.external_id.like("%-hr-%")
        | Measure.external_id.like("%-hjres-%")
        | Measure.external_id.like("%-hconres-%")
        | Measure.external_id.like("%-hres-%")
    ),
)
_is_senate = and_(
    _is_federal,
    (
        Measure.external_id.like("%-s-%")
        | Measure.external_id.like("%-sjres-%")
        | Measure.external_id.like("%-sconres-%")
        | Measure.external_id.like("%-sres-%")
    ),
)
_alignment_match = (
    ((UserVote.vote == "yes") & (Measure.status == "passed"))
    | ((UserVote.vote == "no") & (Measure.status == "failed"))
)
_has_outcome = Measure.status.in_(["passed", "failed"])


def _alignment_cols(chamber_filter, prefix: str):
    """Return (matches, total) aggregate columns for a chamber filter."""
    return [
        func.count(
            case((and_(chamber_filter, _has_outcome, _alignment_match), 1))
        ).label(f"{prefix}_matches"),
        func.count(
            case((and_(chamber_filter, _has_outcome), 1))
        ).label(f"{prefix}_total"),
    ]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's activity dashboard with summary stats.
    Stats computed in SQL; recent activity limited to 5 rows in the query.
    """
    # Try cache
    cache_k = dashboard_key(current_user.id)
    cached = await cache_get(cache_k)
    if cached is not None:
        return DashboardResponse(**cached)

    # --- Aggregate stats in one SQL query ---
    stmt = (
        select(
            func.count(UserVote.measure_id).label("total_votes"),
            func.count(case((UserVote.vote == "yes", 1))).label("yea_votes"),
            func.count(case((UserVote.vote == "no", 1))).label("nay_votes"),
            func.count(case((UserVote.vote == "skip", 1))).label("skipped"),
            func.count(case((Measure.status == "passed", 1))).label("measures_passed"),
            func.count(case((Measure.status == "failed", 1))).label("measures_failed"),
            func.count(
                case(
                    (
                        and_(
                            Measure.status.notin_(["passed", "failed"]),
                        ),
                        1,
                    )
                )
            ).label("measures_pending"),
            # Overall alignment
            func.count(case((_alignment_match, 1))).label("alignment_matches"),
            func.count(case((_has_outcome, 1))).label("alignment_total"),
            # Chamber-level alignment
            *_alignment_cols(_is_house, "house"),
            *_alignment_cols(_is_senate, "senate"),
            *_alignment_cols(_is_federal, "congress"),
        )
        .join(Measure, UserVote.measure_id == Measure.id)
        .where(UserVote.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    row = result.one()

    total_votes = row.total_votes or 0

    def _pct(matches, total):
        if total > 0:
            return round((matches / total) * 100, 1)
        return None

    alignment_score = _pct(row.alignment_matches or 0, row.alignment_total or 0)
    house_alignment = _pct(row.house_matches or 0, row.house_total or 0)
    senate_alignment = _pct(row.senate_matches or 0, row.senate_total or 0)
    congress_alignment = _pct(row.congress_matches or 0, row.congress_total or 0)

    # --- Recent activity: only fetch 5 most recent ---
    recent_stmt = (
        select(UserVote, Measure)
        .join(Measure, UserVote.measure_id == Measure.id)
        .where(UserVote.user_id == current_user.id)
        .order_by(UserVote.created_at.desc())
        .limit(5)
    )
    recent_result = await db.execute(recent_stmt)
    recent_rows = recent_result.fetchall()

    recent_activity = [
        RecentActivity(
            measure_id=m.id,
            title=m.title,
            level=JurisdictionLevel(m.level),
            user_vote=uv.vote,
            voted_at=uv.created_at,
            outcome=m.status if m.status in ("passed", "failed") else None,
        )
        for uv, m in recent_rows
    ]

    resp = DashboardResponse(
        stats=DashboardStats(
            total_votes=total_votes,
            yea_votes=row.yea_votes or 0,
            nay_votes=row.nay_votes or 0,
            skipped=row.skipped or 0,
            measures_passed=row.measures_passed or 0,
            measures_failed=row.measures_failed or 0,
            measures_pending=row.measures_pending or 0,
            alignment_score=alignment_score,
            house_alignment=house_alignment,
            senate_alignment=senate_alignment,
            congress_alignment=congress_alignment,
        ),
        recent_activity=recent_activity,
    )

    await cache_set(cache_k, resp.dict(), ttl=120)  # 2 min
    return resp
