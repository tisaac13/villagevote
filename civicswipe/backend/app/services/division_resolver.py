"""
Division resolution service - maps location to political divisions.
Works for all 50 US states + DC.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models import Division, UserDivision

logger = logging.getLogger(__name__)

# Full state name lookup from 2-letter code
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


class DivisionResolver:
    """
    Resolves a user's location to political divisions (federal, state, city).
    Works for any US state.
    """

    async def resolve_divisions(
        self,
        db: AsyncSession,
        user_id: str,
        lat: float,
        lon: float,
        state: str,
        city: str,
    ) -> List[Division]:
        """
        Resolve location to applicable political divisions.

        Creates divisions for:
        - United States (federal)
        - User's state
        - User's city

        Args:
            db: Database session
            user_id: User UUID
            lat: Latitude
            lon: Longitude
            state: State code (e.g., "AZ", "CA", "NY")
            city: City name

        Returns:
            List of Division objects
        """
        divisions = []
        state_upper = state.strip().upper()
        state_lower = state_upper.lower()
        city_title = city.strip().title()
        city_slug = city.strip().lower().replace(" ", "_")
        state_name = STATE_NAMES.get(state_upper, state_upper)

        try:
            # 1. Federal (always applicable for US residents)
            federal_division = await self._get_or_create_division(
                db,
                division_type="country",
                ocd_id="ocd-division/country:us",
                name="United States",
                level="federal",
            )
            divisions.append(federal_division)

            # 2. State
            state_division = await self._get_or_create_division(
                db,
                division_type="state",
                ocd_id=f"ocd-division/country:us/state:{state_lower}",
                name=state_name,
                level="state",
                parent_id=federal_division.id,
            )
            divisions.append(state_division)

            # 3. City
            if city_title:
                city_division = await self._get_or_create_division(
                    db,
                    division_type="city",
                    ocd_id=f"ocd-division/country:us/state:{state_lower}/place:{city_slug}",
                    name=city_title,
                    level="city",
                    parent_id=state_division.id,
                )
                divisions.append(city_division)

            # Link divisions to user
            await self._link_user_divisions(db, user_id, [d.id for d in divisions])

            return divisions

        except Exception as e:
            logger.error(f"Division resolution failed: {e}")
            return divisions
    
    async def _get_or_create_division(
        self,
        db: AsyncSession,
        division_type: str,
        ocd_id: str,
        name: str,
        level: str,
        parent_id: Optional[str] = None
    ) -> Division:
        """Get existing division or create new one"""
        stmt = select(Division).where(
            Division.division_type == division_type,
            Division.ocd_id == ocd_id
        )
        result = await db.execute(stmt)
        division = result.scalar_one_or_none()
        
        if not division:
            division = Division(
                division_type=division_type,
                ocd_id=ocd_id,
                name=name,
                level=level,
                parent_id=parent_id
            )
            db.add(division)
            await db.flush()
            logger.info(f"Created division: {name} ({ocd_id})")
        
        return division
    
    async def _link_user_divisions(
        self,
        db: AsyncSession,
        user_id: str,
        division_ids: List[str]
    ):
        """Link user to their divisions"""
        # First, remove old divisions
        stmt = select(UserDivision).where(UserDivision.user_id == user_id)
        result = await db.execute(stmt)
        old_links = result.scalars().all()
        
        for old_link in old_links:
            await db.delete(old_link)
        
        # Add new divisions
        for division_id in division_ids:
            user_division = UserDivision(
                user_id=user_id,
                division_id=division_id
            )
            db.add(user_division)
        
        await db.flush()
        logger.info(f"Linked user {user_id} to {len(division_ids)} divisions")


# Global instance
division_resolver = DivisionResolver()
