"""
User onboarding tasks

Background tasks triggered after signup to resolve a user's
geographic location, political divisions, and congressional representatives.
"""
import logging
from typing import Dict, Any
import asyncio

from app.tasks.celery_app import celery_app
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.tasks.user_onboarding.resolve_user_location",
    max_retries=3,
)
def resolve_user_location(
    self,
    user_id: str,
    street: str,
    city: str,
    state: str,
    zip_code: str,
) -> Dict[str, Any]:
    """
    Full onboarding flow after signup:
      1. Geocode address -> lat/lon
      2. Resolve political divisions (federal, state, city)
      3. Look up congressional representatives (2 senators + 1 house rep)

    Updates the user_profile row with lat/lon, creates division links,
    and creates user_officials links.

    Args:
        user_id: UUID string of the newly created user
        street: Street address (line1), plaintext
        city: City name
        state: 2-letter state code
        zip_code: Postal code

    Returns:
        Dict with geocoded coords, division count, and rep count
    """
    logger.info(
        f"Starting location resolution for user {user_id} "
        f"({city}, {state} {zip_code})"
    )

    async def _run():
        from sqlalchemy import select
        from app.models import UserProfile
        from app.services.geocoding import geocoding_service
        from app.services.division_resolver import division_resolver
        from app.services.congress_api import congress_api_service

        result = {
            "user_id": user_id,
            "geocoded": False,
            "lat": None,
            "lon": None,
            "divisions_count": 0,
            "representatives_count": 0,
        }

        async with async_session_maker() as db:
            # Step 1: Geocode address
            coords = await geocoding_service.geocode_address(
                street=street,
                city=city,
                state=state,
                zip_code=zip_code,
            )

            if coords:
                lat, lon = coords
                result["geocoded"] = True
                result["lat"] = lat
                result["lon"] = lon

                # Update user_profile with lat/lon
                stmt = select(UserProfile).where(
                    UserProfile.user_id == user_id
                )
                row = await db.execute(stmt)
                profile = row.scalar_one_or_none()

                if profile:
                    profile.lat = str(lat)
                    profile.lon = str(lon)

                # Step 2: Resolve divisions
                divisions = await division_resolver.resolve_divisions(
                    db=db,
                    user_id=user_id,
                    lat=lat,
                    lon=lon,
                    state=state,
                    city=city,
                )
                result["divisions_count"] = len(divisions)
            else:
                logger.warning(
                    f"Geocoding returned no results for user {user_id} "
                    f"({street}, {city}, {state} {zip_code})"
                )

            # Step 3: Resolve congressional representatives
            # (does its own district lookup via Census Geocoder internally)
            try:
                reps = await congress_api_service.refresh_user_representatives(
                    db=db,
                    user_id=user_id,
                    state=state,
                    street=street,
                    city=city,
                    zip_code=zip_code,
                )
                result["representatives_count"] = len(reps)
            except Exception as e:
                # Don't re-raise; geocoding + divisions may have succeeded
                logger.warning(
                    f"Representative resolution failed for user {user_id}: {e}"
                )

            await db.commit()

        return result

    try:
        stats = run_async(_run())
        logger.info(f"Location resolution completed for user {user_id}: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Location resolution failed for user {user_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
