"""
Federal Data Connector - Congress.gov API

Fetches bills, resolutions, and roll call votes from the U.S. Congress.
API Documentation: https://api.congress.gov/

This connector:
- Fetches recent bills from the House and Senate
- Fetches roll call votes when available
- Maps data to the CivicSwipe schema
- Supports incremental updates
"""
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


class FederalConnector:
    """
    Connector for fetching federal legislation data from Congress.gov API.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.CONGRESS_API_KEY
        if not self.api_key:
            raise ValueError("CONGRESS_API_KEY is not configured")

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Congress.gov API."""
        url = f"{CONGRESS_API_BASE}{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        params["format"] = "json"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_recent_bills(
        self,
        congress: int = 118,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Fetch recent bills from Congress.

        Args:
            congress: Congress number (e.g., 118 for 2023-2024)
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

    async def get_house_votes(self, congress: int, session: int, limit: int = 50) -> List[Dict]:
        """
        Fetch House roll call votes.

        Args:
            congress: Congress number
            session: Session number (1 or 2)
            limit: Number of votes to fetch

        Returns:
            List of vote data
        """
        # Note: Congress.gov API doesn't have a direct roll call endpoint
        # You may need to use clerk.house.gov for detailed roll calls
        # For now, we'll look for bills with recorded votes
        try:
            # Get bills that have had a vote
            data = await self._make_request(
                f"/bill/{congress}",
                params={
                    "limit": limit,
                    "sort": "updateDate+desc"
                }
            )
            return data.get("bills", [])
        except Exception as e:
            logger.error(f"Error fetching House votes: {e}")
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
        congress = bill.get("congress", 118)

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

        if "passed" in action_lower or "agreed to" in action_lower:
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
                    "congress": 118,
                }
            )
            self.db.add(connector)
            await self.db.flush()

        return connector

    async def run(self, congress: int = 118, limit: int = 50) -> Dict[str, Any]:
        """
        Run the federal connector to fetch and store bills.

        Args:
            congress: Congress number to fetch
            limit: Maximum number of bills to process

        Returns:
            Statistics about the ingestion run
        """
        stats = {
            "bills_fetched": 0,
            "new_measures": 0,
            "updated_measures": 0,
            "errors": 0,
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
            # Fetch recent bills
            bills = await self.get_recent_bills(congress=congress, limit=limit)
            stats["bills_fetched"] = len(bills)
            logger.info(f"Fetched {len(bills)} bills from Congress {congress}")

            for bill in bills:
                try:
                    # Map to measure schema
                    measure_data = self._map_bill_to_measure(bill)

                    # Check if measure already exists
                    result = await self.db.execute(
                        select(Measure).where(
                            Measure.source == measure_data["source"],
                            Measure.external_id == measure_data["external_id"]
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        # Update existing measure
                        for key, value in measure_data.items():
                            if value is not None:
                                setattr(existing, key, value)
                        stats["updated_measures"] += 1
                    else:
                        # Create new measure
                        measure = Measure(**measure_data)
                        self.db.add(measure)
                        await self.db.flush()

                        # Add source link
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

        return stats

    def _get_chamber(self, bill_type: str) -> str:
        """Get chamber name from bill type."""
        if bill_type.startswith("h"):
            return "house"
        elif bill_type.startswith("s"):
            return "senate"
        return "house"


async def run_federal_connector(db: AsyncSession, congress: int = 118, limit: int = 50) -> Dict[str, Any]:
    """
    Convenience function to run the federal connector.

    Usage:
        from app.connectors.federal import run_federal_connector
        stats = await run_federal_connector(db, congress=118, limit=100)
    """
    connector = FederalConnector(db)
    return await connector.run(congress=congress, limit=limit)
