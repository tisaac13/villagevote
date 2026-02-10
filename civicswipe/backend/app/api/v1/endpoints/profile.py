"""
Profile endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from datetime import date as date_type, datetime

from app.core.database import get_db
from app.core.security import encrypt_address, hash_address, verify_password
from app.schemas import (
    ProfileResponse, AddressPublic, Location, Preferences, Address,
    UserResponse, ProfileUpdateRequest, ProfileUpdateResponse
)
from app.models import User, UserProfile, UserPreferences
from app.services.geocoding import geocoding_service
from app.services.division_resolver import division_resolver
from app.services.congress_api import congress_api_service
from app.api.deps import get_current_user

router = APIRouter()


def _to_date(val):
    """Safely convert a datetime or date to date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    return val


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
            state=current_user.state or "",
            birthday=_to_date(current_user.birthday),
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


@router.patch("/profile", response_model=ProfileUpdateResponse)
async def update_profile(
    profile_update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile (name, email, birthday).
    Email change requires current_password for verification.
    """
    import logging
    logger = logging.getLogger(__name__)

    changed_fields = []

    # --- Email change: requires password verification ---
    if profile_update.email is not None and profile_update.email != current_user.email:
        # Require current password
        if not profile_update.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to change email"
            )

        # Check user has a password (not OAuth-only)
        if not current_user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change email for social login accounts without a password"
            )

        # Verify password
        if not verify_password(profile_update.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )

        # Check email uniqueness
        existing = await db.execute(
            select(User).where(
                User.email == profile_update.email,
                User.id != current_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use"
            )

        old_email = current_user.email
        current_user.email = profile_update.email
        changed_fields.append("email")
        logger.info(
            f"Profile update: email changed for user {current_user.id}",
            extra={"user_id": str(current_user.id), "field": "email"}
        )

    # --- Name changes ---
    if profile_update.first_name is not None and profile_update.first_name != current_user.first_name:
        current_user.first_name = profile_update.first_name
        changed_fields.append("first_name")

    if profile_update.last_name is not None and profile_update.last_name != current_user.last_name:
        current_user.last_name = profile_update.last_name
        changed_fields.append("last_name")

    # --- Birthday change ---
    if profile_update.birthday is not None:
        # DB column is date type, so assign date directly
        current_bd = current_user.birthday
        # Handle case where stored value might be datetime or date
        if hasattr(current_bd, 'date'):
            current_bd = current_bd.date()
        if profile_update.birthday != current_bd:
            current_user.birthday = profile_update.birthday
            changed_fields.append("birthday")

    if changed_fields:
        await db.commit()
        await db.refresh(current_user)
        logger.info(
            f"Profile updated for user {current_user.id}: {', '.join(changed_fields)}",
            extra={
                "user_id": str(current_user.id),
                "changed_fields": changed_fields,
            }
        )

    return ProfileUpdateResponse(
        updated=len(changed_fields) > 0,
        changed_fields=changed_fields,
        user=UserResponse(
            id=current_user.id,
            email=current_user.email,
            first_name=current_user.first_name or "",
            last_name=current_user.last_name or "",
            state=current_user.state or "",
            birthday=_to_date(current_user.birthday),
        )
    )


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
