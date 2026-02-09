"""
Representatives endpoints - look up and display user's congressional representatives.

Cached in Redis to avoid repeated DB + alignment queries on every app open.
"""
from typing import Optional, Tuple, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, literal_column

from app.core.database import get_db
from app.core.cache import cache_get, cache_set, cache_delete, reps_key
from app.schemas import RepresentativesResponse, RepresentativeItem, RepresentativeRefreshResponse
from app.models import (
    User, UserProfile, Official, UserOfficial,
    UserVote, VoteEvent, OfficialVote, Measure,
)
from app.api.deps import get_current_user
from app.services.congress_api import congress_api_service
from app.core.security import decrypt_address

router = APIRouter()


@router.get("", response_model=RepresentativesResponse)
async def get_representatives(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's congressional representatives with alignment scores.
    Results are cached for 5 minutes per user.
    """
    # Try cache first
    cache_key = reps_key(current_user.id)
    cached = await cache_get(cache_key)
    if cached is not None:
        return RepresentativesResponse(**cached)

    # Check if user has a profile/address
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        resp = RepresentativesResponse(representatives=[], has_address=False)
        await cache_set(cache_key, resp.dict(), ttl=60)
        return resp

    # Get active officials for this user
    stmt = (
        select(Official)
        .join(UserOfficial)
        .where(
            UserOfficial.user_id == current_user.id,
            UserOfficial.active == True,
        )
    )
    result = await db.execute(stmt)
    officials = result.scalars().all()

    if not officials:
        resp = RepresentativesResponse(representatives=[], has_address=True)
        await cache_set(cache_key, resp.dict(), ttl=60)
        return resp

    # Compute alignment for ALL officials in a single query (fixes N+1)
    alignment_map = await _compute_all_alignments(
        db, current_user.id, [o.id for o in officials]
    )

    items = []
    for official in officials:
        alignment, votes_compared = alignment_map.get(
            official.id, (None, 0)
        )
        items.append(
            RepresentativeItem(
                id=official.id,
                name=official.name,
                office=official.office or "",
                party=official.party,
                chamber=official.chamber,
                district_label=official.district_label,
                photo_url=official.photo_url,
                alignment_percentage=alignment,
                votes_compared=votes_compared,
            )
        )

    resp = RepresentativesResponse(representatives=items, has_address=True)
    await cache_set(cache_key, resp.dict(), ttl=300)  # 5 min
    return resp


@router.post("/refresh", response_model=RepresentativeRefreshResponse)
async def refresh_representatives(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-fetch representatives based on user's current address.
    Calls Congress.gov API and Census Geocoder.
    """
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No address on file. Update your address first.",
        )

    try:
        street = decrypt_address(profile.address_line1_enc)
    except Exception:
        street = ""

    reps = await congress_api_service.refresh_user_representatives(
        db=db,
        user_id=current_user.id,
        state=profile.state,
        street=street,
        city=profile.city,
        zip_code=profile.postal_code,
    )

    await db.commit()

    return RepresentativeRefreshResponse(refreshed=True, count=len(reps))


async def _compute_all_alignments(
    db: AsyncSession, user_id, official_ids: List
) -> Dict:
    """
    Compute alignment for multiple officials in ONE query instead of N+1.

    Returns:
        {official_id: (alignment_percentage, votes_compared)}
    """
    if not official_ids:
        return {}

    # User votes subquery
    user_vote_sub = (
        select(
            UserVote.measure_id,
            UserVote.vote.label("user_vote"),
        )
        .where(UserVote.user_id == user_id)
        .subquery()
    )

    # Official votes subquery — includes official_id so we can group
    official_vote_sub = (
        select(
            OfficialVote.official_id,
            VoteEvent.measure_id,
            OfficialVote.vote.label("official_vote"),
        )
        .join(VoteEvent, OfficialVote.vote_event_id == VoteEvent.id)
        .where(OfficialVote.official_id.in_(official_ids))
        .subquery()
    )

    # Join and aggregate per official
    # Count matches and total comparable votes in SQL
    is_comparable = and_(
        official_vote_sub.c.official_vote.notin_(
            ["unknown", "absent", "not_voting", "present"]
        )
    )
    is_match = case(
        (
            and_(
                is_comparable,
                (
                    (user_vote_sub.c.user_vote == "yes")
                    & (official_vote_sub.c.official_vote == "yea")
                )
                | (
                    (user_vote_sub.c.user_vote == "no")
                    & (official_vote_sub.c.official_vote == "nay")
                ),
            ),
            1,
        ),
        else_=0,
    )
    is_counted = case((is_comparable, 1), else_=0)

    stmt = (
        select(
            official_vote_sub.c.official_id,
            func.sum(is_match).label("matches"),
            func.sum(is_counted).label("total"),
        )
        .join(
            user_vote_sub,
            official_vote_sub.c.measure_id == user_vote_sub.c.measure_id,
        )
        .group_by(official_vote_sub.c.official_id)
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    alignment_map = {}
    for official_id, matches, total in rows:
        matches = int(matches or 0)
        total = int(total or 0)
        if total > 0:
            alignment_map[official_id] = (round((matches / total) * 100, 1), total)
        else:
            alignment_map[official_id] = (None, 0)

    return alignment_map
