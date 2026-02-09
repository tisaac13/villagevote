"""
Profile endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import encrypt_address, hash_address
from app.schemas import ProfileResponse, AddressPublic, Location, Preferences, Address, UserResponse
from app.models import User, UserProfile, UserPreferences
from app.services.geocoding import geocoding_service
from app.services.division_resolver import division_resolver
from app.services.congress_api import congress_api_service
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile"""
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    stmt = select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    result = await db.execute(stmt)
    preferences = result.scalar_one_or_none()

    return ProfileResponse(
        user=UserResponse(
            id=current_user.id,
            email=current_user.email,
            first_name=current_user.first_name or "",
            last_name=current_user.last_name or "",
            state=current_user.state or ""
        ),
        address=AddressPublic(
            city=profile.city if profile else "",
            state=profile.state if profile else current_user.state or "",
            postal_code=profile.postal_code if profile else "",
            country=profile.country if profile else "US"
        ) if profile else None,
        location=Location(
            lat=float(profile.lat) if profile and profile.lat else None,
            lon=float(profile.lon) if profile and profile.lon else None
        ),
        preferences=Preferences(
            topics=preferences.topics if preferences else [],
            notify_enabled=preferences.notify_enabled if preferences else True
        )
    )


@router.patch("/address")
async def update_address(
    address: Address,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user address and re-resolve divisions"""
    coords = await geocoding_service.geocode_address(
        street=address.line1,
        city=address.city,
        state=address.state,
        zip_code=address.postal_code
    )
    
    stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    
    profile.address_line1_enc = encrypt_address(address.line1)
    profile.address_line2_enc = encrypt_address(address.line2) if address.line2 else None
    profile.city = address.city
    profile.state = address.state
    profile.postal_code = address.postal_code
    profile.country = address.country
    profile.address_hash = hash_address(
        address.line1, address.city, address.state, address.postal_code, address.country
    )
    
    if coords:
        profile.lat = str(coords[0])
        profile.lon = str(coords[1])
        await division_resolver.resolve_divisions(
            db=db, user_id=current_user.id, lat=coords[0], lon=coords[1],
            state=address.state, city=address.city
        )

    # Refresh congressional representatives based on new address
    reps_count = 0
    try:
        reps = await congress_api_service.refresh_user_representatives(
            db=db,
            user_id=current_user.id,
            state=address.state,
            street=address.line1,
            city=address.city,
            zip_code=address.postal_code,
        )
        reps_count = len(reps)
    except Exception as e:
        # Don't fail the address update if rep lookup fails
        import logging
        logging.getLogger(__name__).warning(f"Representative refresh failed: {e}")

    await db.commit()
    return {
        "updated": True,
        "divisions_recomputed": coords is not None,
        "representatives_found": reps_count,
    }


@router.patch("/preferences")
async def update_preferences(
    preferences: Preferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences"""
    stmt = select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    result = await db.execute(stmt)
    user_prefs = result.scalar_one_or_none()
    
    if not user_prefs:
        user_prefs = UserPreferences(user_id=current_user.id)
        db.add(user_prefs)
    
    user_prefs.topics = preferences.topics
    user_prefs.notify_enabled = preferences.notify_enabled
    await db.commit()
    
    return {"updated": True}
