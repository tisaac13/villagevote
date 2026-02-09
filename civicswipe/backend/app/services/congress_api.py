"""
Congress.gov API service for representative lookup.

Uses Congress.gov API to fetch current members of Congress,
and Census Geocoder to resolve addresses to congressional districts.

Works for all 50 US states + DC.

API docs: https://api.congress.gov/
Census Geocoder: https://geocoding.geo.census.gov/geocoder/
"""
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import logging

from app.core.config import settings
from app.models import Official, UserOfficial, OfficialDivision, Division

logger = logging.getLogger(__name__)

CONGRESS_API_BASE = "https://api.congress.gov/v3"
CENSUS_GEOCODER_BASE = "https://geocoding.geo.census.gov/geocoder"

# Current congress number
CURRENT_CONGRESS = 119


class CongressApiService:
    """
    Looks up a user's congressional representatives (2 Senators + 1 House Rep)
    using Congress.gov API and Census Geocoder for district resolution.
    Works for all 50 US states + DC.
    """

    async def _congress_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Congress.gov API."""
        url = f"{CONGRESS_API_BASE}{endpoint}"
        params = params or {}
        params["api_key"] = settings.CONGRESS_API_KEY
        params["format"] = "json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_congressional_district(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str
    ) -> Optional[int]:
        """
        Use Census Geocoder to determine congressional district from address.
        Works for any US address.

        Returns:
            Congressional district number, or None if lookup fails.
        """
        try:
            url = f"{CENSUS_GEOCODER_BASE}/geographies/address"
            params = {
                "street": street,
                "city": city,
                "state": state,
                "zip": zip_code,
                "benchmark": "Public_AR_Current",
                "vintage": "Current_Current",
                "layers": "54",  # Congressional Districts
                "format": "json",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            matches = data.get("result", {}).get("addressMatches", [])
            if not matches:
                logger.warning(f"No address match from Census Geocoder for {city}, {state}")
                return None

            geographies = matches[0].get("geographies", {})

            # Look for congressional district in any matching key
            for key in geographies:
                if "Congressional" in key:
                    districts = geographies[key]
                    if districts:
                        cd = districts[0].get("BASENAME", districts[0].get("CD119FP", districts[0].get("CD", "")))
                        if cd is not None and str(cd).isdigit():
                            return int(cd)

            logger.warning(f"No congressional district found for {city}, {state}")
            return None

        except Exception as e:
            logger.error(f"Census Geocoder lookup failed: {e}")
            return None

    async def get_senators_by_state(self, state_code: str) -> List[Dict[str, Any]]:
        """
        Fetch current senators for a given state using the state-specific endpoint.
        The Congress.gov API /member/{stateCode} returns all current members for that state.
        """
        try:
            data = await self._congress_request(
                f"/member/{state_code.upper()}",
                params={
                    "currentMember": "true",
                    "limit": 20,
                }
            )

            senators = []
            for member in data.get("members", []):
                terms = member.get("terms", {}).get("item", [])
                if not terms:
                    continue

                latest_term = terms[0]
                chamber = latest_term.get("chamber", "")

                if chamber == "Senate":
                    senators.append(self._parse_member(member, latest_term))

            return senators

        except Exception as e:
            logger.error(f"Failed to fetch senators for {state_code}: {e}")
            return []

    async def get_house_rep_by_district(
        self, state_code: str, district: int
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the House representative for a state + district.
        Uses the state-specific endpoint and filters by district number.
        """
        try:
            data = await self._congress_request(
                f"/member/{state_code.upper()}",
                params={
                    "currentMember": "true",
                    "limit": 60,  # Some states have 50+ districts (CA, TX)
                }
            )

            for member in data.get("members", []):
                terms = member.get("terms", {}).get("item", [])
                if not terms:
                    continue

                latest_term = terms[0]
                chamber = latest_term.get("chamber", "")
                member_district = latest_term.get("district")

                if (
                    chamber == "House of Representatives"
                    and member_district is not None
                    and int(member_district) == district
                ):
                    return self._parse_member(member, latest_term)

            logger.warning(f"No House rep found for {state_code}-{district}")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch House rep for {state_code}-{district}: {e}")
            return None

    def _parse_member(self, member: Dict, term: Dict) -> Dict[str, Any]:
        """Parse a Congress.gov member response into our standard format."""
        bioguide_id = member.get("bioguideId", "")
        chamber = term.get("chamber", "")
        district = term.get("district")

        if chamber == "Senate":
            office = "U.S. Senator"
            chamber_key = "us_senate"
            district_label = term.get("stateCode", "")
        else:
            office = "U.S. Representative"
            chamber_key = "us_house"
            district_label = f"CD-{int(district):02d}" if district else ""

        return {
            "bioguide_id": bioguide_id,
            "name": member.get("name", ""),
            "party": term.get("party", member.get("partyName", "")),
            "office": office,
            "chamber": chamber_key,
            "district_label": district_label,
            "state": term.get("stateCode", ""),
            "photo_url": member.get("depiction", {}).get("imageUrl", ""),
        }

    async def refresh_user_representatives(
        self,
        db: AsyncSession,
        user_id: str,
        state: str,
        street: str,
        city: str,
        zip_code: str,
    ) -> List[Dict[str, Any]]:
        """
        Full flow: look up congressional district, fetch senators + house rep,
        upsert into officials table, and link to user via user_officials.
        Works for any US state.

        Returns:
            List of representative dicts that were linked to the user.
        """
        representatives = []

        # 1. Get senators by state (works for all 50 states + DC)
        senators = await self.get_senators_by_state(state)
        representatives.extend(senators)

        # 2. Get congressional district and house rep
        district = await self.get_congressional_district(street, city, state, zip_code)
        if district is not None:
            house_rep = await self.get_house_rep_by_district(state, district)
            if house_rep:
                representatives.append(house_rep)
        else:
            logger.warning(f"Could not determine district for {city}, {state} - skipping House rep")

        if not representatives:
            logger.warning(f"No representatives found for user {user_id} in {state}")
            return []

        # 3. Upsert officials and link to user
        official_ids = []
        for rep in representatives:
            official = await self._upsert_official(db, rep)
            official_ids.append(official.id)

        # 4. Replace user_officials links (deactivate old, add new)
        await self._replace_user_officials(db, user_id, official_ids)

        await db.flush()
        logger.info(f"Linked {len(official_ids)} representatives to user {user_id}")

        return representatives

    async def _upsert_official(self, db: AsyncSession, rep: Dict[str, Any]) -> Official:
        """Insert or update an official based on bioguide_id."""
        external_id = f"congress:{rep['bioguide_id']}"

        stmt = select(Official).where(Official.external_id == external_id)
        result = await db.execute(stmt)
        official = result.scalar_one_or_none()

        if official:
            official.name = rep["name"]
            official.party = rep["party"]
            official.office = rep["office"]
            official.chamber = rep["chamber"]
            official.district_label = rep["district_label"]
            official.photo_url = rep.get("photo_url")
        else:
            official = Official(
                external_id=external_id,
                name=rep["name"],
                party=rep["party"],
                office=rep["office"],
                chamber=rep["chamber"],
                district_label=rep["district_label"],
                photo_url=rep.get("photo_url"),
            )
            db.add(official)
            await db.flush()

        return official

    async def _replace_user_officials(
        self, db: AsyncSession, user_id: str, official_ids: List
    ):
        """Deactivate old user_officials and create new active links."""
        # Deactivate all existing
        stmt = select(UserOfficial).where(
            UserOfficial.user_id == user_id,
            UserOfficial.active == True,
        )
        result = await db.execute(stmt)
        existing = result.scalars().all()
        for uo in existing:
            uo.active = False

        # Create new active links
        for official_id in official_ids:
            # Check if link already exists
            stmt = select(UserOfficial).where(
                UserOfficial.user_id == user_id,
                UserOfficial.official_id == official_id,
            )
            result = await db.execute(stmt)
            existing_link = result.scalar_one_or_none()

            if existing_link:
                existing_link.active = True
            else:
                db.add(UserOfficial(
                    user_id=user_id,
                    official_id=official_id,
                    active=True,
                ))


# Global instance
congress_api_service = CongressApiService()
