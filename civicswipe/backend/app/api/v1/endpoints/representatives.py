"""
Representatives endpoints - look up and display user's congressional representatives
"""
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
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
    """
    # Check if user has a profile/address
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return RepresentativesResponse(representatives=[], has_address=False)

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
        return RepresentativesResponse(representatives=[], has_address=True)

    # Calculate alignment for each official
    items = []
    for official in officials:
        alignment, votes_compared = await _compute_alignment(
            db, current_user.id, official.id
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

    return RepresentativesResponse(representatives=items, has_address=True)


@router.post("/refresh", response_model=RepresentativeRefreshResponse)
async def refresh_representatives(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-fetch representatives based on user's current address.
    Calls Congress.gov API and Census Geocoder.
    """
    # Get user profile with address
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No address on file. Update your address first.",
        )

    # Decrypt address line1 for geocoding
    try:
        street = decrypt_address(profile.address_line1_enc)
    except Exception:
        street = ""

    reps = await congress_api_service.refresh_user_representatives(
        db=db,
        user_id=str(current_user.id),
        state=profile.state,
        street=street,
        city=profile.city,
        zip_code=profile.postal_code,
    )

    await db.commit()

    return RepresentativeRefreshResponse(refreshed=True, count=len(reps))


async def _compute_alignment(
    db: AsyncSession, user_id, official_id
) -> Tuple[Optional[float], int]:
    """
    Compute alignment percentage between a user and a specific official.

    Returns:
        (alignment_percentage or None, votes_compared)
    """
    # Get measures where both the user AND this official voted
    # User votes
    user_vote_sub = (
        select(
            UserVote.measure_id,
            UserVote.vote.label("user_vote"),
        )
        .where(UserVote.user_id == user_id)
        .subquery()
    )

    # Official votes (through vote_events)
    official_vote_sub = (
        select(
            VoteEvent.measure_id,
            OfficialVote.vote.label("official_vote"),
        )
        .join(OfficialVote, OfficialVote.vote_event_id == VoteEvent.id)
        .where(OfficialVote.official_id == official_id)
        .subquery()
    )

    # Join them
    stmt = select(
        user_vote_sub.c.user_vote,
        official_vote_sub.c.official_vote,
    ).join(
        official_vote_sub,
        user_vote_sub.c.measure_id == official_vote_sub.c.measure_id,
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    if not rows:
        return None, 0

    matches = 0
    total = 0
    for user_vote, official_vote in rows:
        if official_vote in ("unknown", "absent", "not_voting", "present"):
            continue
        total += 1
        # yes -> yea, no -> nay
        if (user_vote == "yes" and official_vote == "yea") or (
            user_vote == "no" and official_vote == "nay"
        ):
            matches += 1

    if total == 0:
        return None, 0

    return round((matches / total) * 100, 1), total
