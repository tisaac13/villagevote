"""
Federal Data Connector - Congress.gov API

Fetches bills, resolutions, and roll call votes from the U.S. Congress.
API Documentation: https://api.congress.gov/

This connector:
- Fetches recent bills from the House and Senate
- Fetches roll call votes when available
- Maps data to the CivicSwipe schema
- Supports incremental updates
- Supports full pagination for loading all bills in a congress
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.models import Measure, MeasureSource, MeasureStatusEvent, VoteEvent, OfficialVote, Connector, IngestionRun

logger = logging.getLogger(__name__)

# Congress.gov API base URL
CONGRESS_API_BASE = "https://api.congress.gov/v3"

# Current congress number
CURRENT_CONGRESS = 119


class FederalConnector:
    """
    Connector for fetching federal legislation data from Congress.gov API.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.CONGRESS_API_KEY
        if not self.api_key:
            raise ValueError("CONGRESS_API_KEY is not configured")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create a shared httpx client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _close_client(self):
        """Close the httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Congress.gov API."""
        url = f"{CONGRESS_API_BASE}{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        params["format"] = "json"

        client = await self._get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_recent_bills(
        self,
        congress: int = CURRENT_CONGRESS,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch recent bills from Congress.

        Args:
            congress: Congress number (e.g., 119 for 2025-2026)
            limit: Number of bills to fetch (max 250)
            offset: Pagination offset

        Returns:
            List of bill data dictionaries
        """
        try:
            data = await self._make_request(
                f"/bill/{congress}",
                params={"limit": min(limit, 250), "offset": offset}
            )
            return data.get("bills", [])
        except Exception as e:
            logger.error(f"Error fetching bills: {e}")
            return []

    async def get_enacted_laws(
        self,
        congress: int = CURRENT_CONGRESS,
        limit: int = 250,
    ) -> List[Dict]:
        """
        Fetch all enacted public laws for a congress via /law/{congress}/pub.
        Paginates automatically.
        """
        all_laws = []
        offset = 0
        page_size = min(limit, 250)
        while True:
            try:
                data = await self._make_request(
                    f"/law/{congress}/pub",
                    params={"limit": page_size, "offset": offset}
                )
                # API returns laws under "bills" key
                laws = data.get("bills", data.get("laws", []))
                if not laws:
                    break
                all_laws.extend(laws)
                logger.info(f"Fetched {len(laws)} laws at offset {offset} (total: {len(all_laws)})")
                offset += len(laws)
                if len(laws) < page_size:
                    break
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error fetching laws at offset {offset}: {e}")
                break
        return all_laws

    async def get_house_roll_call_votes(
        self,
        congress: int = CURRENT_CONGRESS,
        limit: int = 250,
    ) -> List[Dict]:
        """
        Fetch all House roll call votes for a congress via /house-vote/{congress}.
        Returns vote records that include legislationNumber and legislationUrl.
        Paginates automatically.
        """
        all_votes = []
        offset = 0
        page_size = min(limit, 250)
        while True:
            try:
                data = await self._make_request(
                    f"/house-vote/{congress}",
                    params={"limit": page_size, "offset": offset}
                )
                votes = data.get("houseRollCallVotes", data.get("houseVotes", data.get("votes", [])))
                if not votes:
                    break
                all_votes.extend(votes)
                logger.info(f"Fetched {len(votes)} house votes at offset {offset} (total: {len(all_votes)})")
                offset += len(votes)
                if len(votes) < page_size:
                    break
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error fetching house votes at offset {offset}: {e}")
                break
        return all_votes

    async def get_bill_details(self, congress: int, bill_type: str, bill_number: int) -> Optional[Dict]:
        """
        Fetch detailed information about a specific bill.

        Args:
            congress: Congress number
            bill_type: Bill type (hr, s, hjres, sjres, hconres, sconres, hres, sres)
            bill_number: Bill number

        Returns:
            Bill details dictionary or None
        """
        try:
            data = await self._make_request(f"/bill/{congress}/{bill_type}/{bill_number}")
            return data.get("bill")
        except Exception as e:
            logger.error(f"Error fetching bill details: {e}")
            return None

    async def get_bill_actions(self, congress: int, bill_type: str, bill_number: int) -> List[Dict]:
        """Fetch actions/timeline for a bill."""
        try:
            data = await self._make_request(
                f"/bill/{congress}/{bill_type}/{bill_number}/actions",
                params={"limit": 100}
            )
            return data.get("actions", [])
        except Exception as e:
            logger.error(f"Error fetching bill actions: {e}")
            return []

    def _map_bill_to_measure(self, bill: Dict, details: Optional[Dict] = None) -> Dict:
        """
        Map Congress.gov bill data to CivicSwipe Measure schema.

        Args:
            bill: Bill data from API
            details: Optional detailed bill data

        Returns:
            Dictionary ready for Measure creation
        """
        # Extract bill info
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", CURRENT_CONGRESS)

        # Build external ID
        external_id = f"{congress}-{bill_type}-{bill_number}"

        # Map status
        status = self._map_status(bill.get("latestAction", {}).get("text", ""))

        # Get dates
        introduced_at = None
        if "introducedDate" in bill:
            try:
                introduced_at = datetime.fromisoformat(bill["introducedDate"])
            except (ValueError, TypeError):
                pass

        updated_at = None
        if "updateDate" in bill:
            try:
                updated_at = datetime.fromisoformat(bill["updateDate"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Build title
        title = bill.get("title", f"{bill_type.upper()} {bill_number}")

        # Extract topics from policy area
        topics = []
        if details and "policyArea" in details:
            topics.append(details["policyArea"].get("name", ""))
        if details and "subjects" in details:
            for subject in details.get("subjects", {}).get("legislativeSubjects", []):
                topics.append(subject.get("name", ""))

        return {
            "source": "congress",
            "external_id": external_id,
            "title": title,
            "level": "federal",
            "status": status,
            "introduced_at": introduced_at,
            "topic_tags": [t for t in topics if t][:10],  # Limit to 10 tags
            "canonical_key": f"us:congress:{congress}:{bill_type}:{bill_number}",
        }

    def _map_status(self, action_text: str) -> str:
        """Map action text to status enum."""
        action_lower = action_text.lower()

        if "became public law" in action_lower or "signed by president" in action_lower:
            return "passed"
        elif "passed" in action_lower or "agreed to" in action_lower:
            return "passed"
        elif "failed" in action_lower or "rejected" in action_lower:
            return "failed"
        elif "referred to" in action_lower or "committee" in action_lower:
            return "in_committee"
        elif "introduced" in action_lower or "sponsor" in action_lower:
            return "introduced"
        elif "scheduled" in action_lower or "calendar" in action_lower:
            return "scheduled"
        elif "tabled" in action_lower:
            return "tabled"
        elif "withdrawn" in action_lower:
            return "withdrawn"
        else:
            return "unknown"

    async def _get_or_create_connector(self) -> Connector:
        """Get or create the federal connector record."""
        result = await self.db.execute(
            select(Connector).where(Connector.name == "congress")
        )
        connector = result.scalar_one_or_none()

        if not connector:
            connector = Connector(
                name="congress",
                source="congress",
                enabled=True,
                config={
                    "base_url": CONGRESS_API_BASE,
                    "congress": CURRENT_CONGRESS,
                }
            )
            self.db.add(connector)
            await self.db.flush()

        return connector

    def _map_law_to_bill(self, law: Dict, congress: int) -> Dict:
        """
        Convert a /law/{congress}/pub response item into a bill-like dict.
        The API returns items that look like bills with type, number, title, latestAction, etc.
        """
        # The law endpoint returns bill-like objects directly
        # type = "S" or "HR", number = "3424", etc.
        bill_type = law.get("type", "hr").lower()
        bill_number = str(law.get("number", ""))

        # Use the latestAction from the response (e.g. "Became Public Law No: 119-76.")
        latest_action = law.get("latestAction", {}).get("text", "Became Public Law")

        return {
            "type": bill_type,
            "number": bill_number,
            "congress": congress,
            "title": law.get("title", f"Public Law {bill_number}"),
            "latestAction": {"text": latest_action},
            "introducedDate": None,
            "updateDate": law.get("updateDate"),
        }

    def _extract_bill_from_house_vote(self, vote: Dict, congress: int) -> Optional[Dict]:
        """
        Convert a /house-vote response item into a bill-like dict.
        Vote items have: legislationType, legislationNumber, result, etc.
        Returns None if not linked to a bill (e.g. procedural motions).
        """
        leg_type = (vote.get("legislationType") or "").strip().upper()
        leg_num = vote.get("legislationNumber")
        if not leg_num:
            return None

        # Map legislationType to bill type (API uses short forms like HR, S, HJRES)
        type_map = {
            "HR": "hr", "H.R.": "hr", "H R": "hr",
            "S": "s", "S.": "s",
            "HJRES": "hjres", "H.J.RES.": "hjres", "H J RES": "hjres",
            "SJRES": "sjres", "S.J.RES.": "sjres", "S J RES": "sjres",
            "HCONRES": "hconres", "H.CON.RES.": "hconres", "H CON RES": "hconres",
            "SCONRES": "sconres", "S.CON.RES.": "sconres", "S CON RES": "sconres",
            "HRES": "hres", "H.RES.": "hres", "H RES": "hres",
            "SRES": "sres", "S.RES.": "sres", "S RES": "sres",
        }
        bill_type = type_map.get(leg_type)
        if not bill_type:
            logger.debug(f"Unknown house vote legislationType: {leg_type}")
            return None

        result_text = vote.get("result", "")
        action_text = f"House roll call vote: {result_text}"

        return {
            "type": bill_type,
            "number": str(leg_num),
            "congress": congress,
            "title": vote.get("title", f"{leg_type} {leg_num}"),
            "latestAction": {"text": action_text},
            "introducedDate": None,
            "updateDate": vote.get("updateDate"),
        }

    async def _upsert_bill(self, bill: Dict, congress: int, stats: Dict):
        """Upsert a single bill into the measures table."""
        measure_data = self._map_bill_to_measure(bill)

        result = await self.db.execute(
            select(Measure).where(
                Measure.source == measure_data["source"],
                Measure.external_id == measure_data["external_id"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in measure_data.items():
                if value is not None:
                    setattr(existing, key, value)
            stats["updated_measures"] += 1
        else:
            measure = Measure(**measure_data)
            self.db.add(measure)
            await self.db.flush()

            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number", "")
            source_url = f"https://www.congress.gov/bill/{congress}th-congress/{self._get_chamber(bill_type)}-bill/{bill_number}"

            source = MeasureSource(
                measure_id=measure.id,
                label="Congress.gov",
                url=source_url,
                ctype="html",
                is_primary=True
            )
            self.db.add(source)
            stats["new_measures"] += 1

    async def run(self, congress: int = CURRENT_CONGRESS, limit: int = 50, fetch_all: bool = False) -> Dict[str, Any]:
        """
        Run the federal connector to fetch and store bills.

        Args:
            congress: Congress number to fetch
            limit: Maximum number of bills to process per page
            fetch_all: If True, fetch enacted laws + bills with House votes
                       (much faster than paginating all bills)

        Returns:
            Statistics about the ingestion run
        """
        stats = {
            "bills_fetched": 0,
            "new_measures": 0,
            "updated_measures": 0,
            "errors": 0,
            "laws_fetched": 0,
            "voted_bills_fetched": 0,
        }

        # Get or create connector
        connector = await self._get_or_create_connector()

        # Create ingestion run
        run = IngestionRun(
            connector_id=connector.id,
            status="running",
            stats={}
        )
        self.db.add(run)
        await self.db.flush()

        try:
            if fetch_all:
                # Strategy: fetch enacted laws + bills with House floor votes
                # This gives us all "historical" bills without fetching thousands of in-committee bills
                seen_external_ids = set()

                # 1. Fetch enacted public laws
                laws = await self.get_enacted_laws(congress=congress)
                stats["laws_fetched"] = len(laws)
                logger.info(f"Fetched {len(laws)} enacted laws")

                for law in laws:
                    try:
                        bill = self._map_law_to_bill(law, congress)
                        ext_id = f"{congress}-{bill['type']}-{bill['number']}"
                        seen_external_ids.add(ext_id)
                        await self._upsert_bill(bill, congress, stats)
                        stats["bills_fetched"] += 1
                    except Exception as e:
                        logger.error(f"Error processing law: {e}")
                        stats["errors"] += 1

                # 2. Fetch bills that had House floor votes
                house_votes = await self.get_house_roll_call_votes(congress=congress)
                for hv in house_votes:
                    try:
                        bill = self._extract_bill_from_house_vote(hv, congress)
                        if not bill:
                            continue
                        ext_id = f"{congress}-{bill['type']}-{bill['number']}"
                        if ext_id in seen_external_ids:
                            continue  # Already processed via laws
                        seen_external_ids.add(ext_id)
                        await self._upsert_bill(bill, congress, stats)
                        stats["bills_fetched"] += 1
                        stats["voted_bills_fetched"] += 1
                    except Exception as e:
                        logger.error(f"Error processing house vote bill: {e}")
                        stats["errors"] += 1

                # 3. Also fetch the most recent bills (upcoming)
                recent_bills = await self.get_recent_bills(congress=congress, limit=limit)
                for bill in recent_bills:
                    try:
                        measure_data = self._map_bill_to_measure(bill)
                        ext_id = measure_data["external_id"]
                        if ext_id in seen_external_ids:
                            continue
                        seen_external_ids.add(ext_id)
                        await self._upsert_bill(bill, congress, stats)
                        stats["bills_fetched"] += 1
                    except Exception as e:
                        logger.error(f"Error processing recent bill: {e}")
                        stats["errors"] += 1
            else:
                bills = await self.get_recent_bills(congress=congress, limit=limit)
                stats["bills_fetched"] = len(bills)
                for bill in bills:
                    try:
                        await self._upsert_bill(bill, congress, stats)
                    except Exception as e:
                        logger.error(f"Error processing bill {bill.get('number')}: {e}")
                        stats["errors"] += 1

            # Update run status
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            run.stats = stats

            await self.db.commit()
            logger.info(f"Federal connector completed: {stats}")

        except Exception as e:
            logger.error(f"Federal connector failed: {e}")
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(e)
            run.stats = stats
            await self.db.commit()
            raise
        finally:
            await self._close_client()

        return stats

    def _get_chamber(self, bill_type: str) -> str:
        """Get chamber name from bill type."""
        if bill_type.startswith("h"):
            return "house"
        elif bill_type.startswith("s"):
            return "senate"
        return "house"


async def run_federal_connector(db: AsyncSession, congress: int = CURRENT_CONGRESS, limit: int = 50, fetch_all: bool = False) -> Dict[str, Any]:
    """
    Convenience function to run the federal connector.

    Usage:
        from app.connectors.federal import run_federal_connector
        stats = await run_federal_connector(db, congress=119, limit=100)
    """
    connector = FederalConnector(db)
    return await connector.run(congress=congress, limit=limit, fetch_all=fetch_all)
