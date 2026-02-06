"""
Division resolution service - maps coordinates to political divisions
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models import Division, UserDivision

logger = logging.getLogger(__name__)


class DivisionResolver:
    """
    Resolves geographic coordinates to political divisions (jurisdictions)
    """
    
    async def resolve_divisions(
        self,
        db: AsyncSession,
        user_id: str,
        lat: float,
        lon: float,
        state: str,
        city: str
    ) -> List[Division]:
        """
        Resolve coordinates and location to all applicable divisions
        
        For Phoenix, AZ user, this returns:
        - United States (country, federal level)
        - Arizona (state)
        - Maricopa County (county)
        - Phoenix (city)
        - Congressional District
        - State Legislative Districts (upper + lower)
        - City Council District
        
        Args:
            db: Database session
            user_id: User UUID
            lat: Latitude
            lon: Longitude
            state: State code (e.g., "AZ")
            city: City name (e.g., "Phoenix")
        
        Returns:
            List of Division objects
        """
        divisions = []
        
        try:
            # 1. Federal (always applicable for US residents)
            federal_division = await self._get_or_create_division(
                db,
                division_type="country",
                ocd_id="ocd-division/country:us",
                name="United States",
                level="federal"
            )
            divisions.append(federal_division)
            
            # 2. State
            if state.upper() == "AZ":
                state_division = await self._get_or_create_division(
                    db,
                    division_type="state",
                    ocd_id="ocd-division/country:us/state:az",
                    name="Arizona",
                    level="state",
                    parent_id=federal_division.id
                )
                divisions.append(state_division)
                
                # 3. County (if Phoenix -> Maricopa County)
                if city.lower() == "phoenix":
                    county_division = await self._get_or_create_division(
                        db,
                        division_type="county",
                        ocd_id="ocd-division/country:us/state:az/county:maricopa",
                        name="Maricopa County",
                        level="county",
                        parent_id=state_division.id
                    )
                    divisions.append(county_division)
                    
                    # 4. City
                    city_division = await self._get_or_create_division(
                        db,
                        division_type="city",
                        ocd_id="ocd-division/country:us/state:az/place:phoenix",
                        name="Phoenix",
                        level="city",
                        parent_id=county_division.id
                    )
                    divisions.append(city_division)
                    
                    # 5. Congressional District (would need API/shapefile lookup)
                    # TODO: Implement actual district lookup based on coordinates
                    # For now, use a placeholder
                    logger.info(f"TODO: Lookup congressional district for {lat}, {lon}")
                    
                    # 6. State Legislative Districts
                    # TODO: Implement AZ legislative district lookup
                    logger.info(f"TODO: Lookup AZ legislative districts for {lat}, {lon}")
                    
                    # 7. City Council District
                    # TODO: Implement Phoenix council district lookup
                    logger.info(f"TODO: Lookup Phoenix council district for {lat}, {lon}")
            
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
