"""
Arizona State Connector - Open States API v3

Fetches bills and votes from the Arizona State Legislature.
API Documentation: https://docs.openstates.org/api-v3/

This connector:
- Fetches recent bills from the Arizona Legislature
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

from app.core.config import settings
from app.models import Measure, MeasureSource, MeasureStatusEvent, VoteEvent, OfficialVote, Connector, IngestionRun

logger = logging.getLogger(__name__)

# Open States API base URL
OPENSTATES_API_BASE = "https://v3.openstates.org"

# Arizona jurisdiction ID
ARIZONA_JURISDICTION = "ocd-jurisdiction/country:us/state:az/government"


class ArizonaConnector:
    """
    Connector for fetching Arizona state legislation data from Open States API.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.api_key = settings.OPENSTATES_API_KEY
        if not self.api_key:
            raise ValueError("OPENSTATES_API_KEY is not configured")

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Open States API."""
        url = f"{OPENSTATES_API_BASE}{endpoint}"
        params = params or {}
        headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_recent_bills(
        self,
        session: Optional[str] = None,
        limit: int = 50,
        page: int = 1
    ) -> List[Dict]:
        """
        Fetch recent bills from Arizona Legislature.

        Args:
            session: Legislative session (e.g., "56th-1st-regular")
            limit: Number of bills to fetch (max 50 per page)
            page: Page number for pagination

        Returns:
            List of bill data dictionaries
        """
        try:
            params = {
                "jurisdiction": "az",  # Use short form instead of full OCD ID
                "per_page": min(limit, 50),
                "page": page,
            }

            if session:
                params["session"] = session

            data = await self._make_request("/bills", params=params)
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching Arizona bills: {e}")
            return []

    async def get_bill_details(self, bill_id: str) -> Optional[Dict]:
        """
        Fetch detailed information about a specific bill.

        Args:
            bill_id: Open States bill ID (e.g., "ocd-bill/...")

        Returns:
            Bill details dictionary or None
        """
        try:
            # URL encode the bill ID
            encoded_id = bill_id.replace("/", "%2F")
            data = await self._make_request(f"/bills/{encoded_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching bill details for {bill_id}: {e}")
            return None

    async def get_bill_votes(self, bill_id: str) -> List[Dict]:
        """Fetch votes for a specific bill."""
        try:
            encoded_id = bill_id.replace("/", "%2F")
            data = await self._make_request(f"/bills/{encoded_id}/votes")
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error fetching votes for {bill_id}: {e}")
            return []

    def _map_bill_to_measure(self, bill: Dict) -> Dict:
        """
        Map Open States bill data to CivicSwipe Measure schema.

        Args:
            bill: Bill data from API

        Returns:
            Dictionary ready for Measure creation
        """
        # Extract bill identifiers
        bill_id = bill.get("id", "")
        identifier = bill.get("identifier", "")
        session = bill.get("session", "")

        # Build external ID
        external_id = f"az-{session}-{identifier}".lower().replace(" ", "-")

        # Map status
        status = self._map_status(bill)

        # Get dates
        introduced_at = None
        first_action = bill.get("first_action_date")
        if first_action:
            try:
                introduced_at = datetime.fromisoformat(first_action.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Build title
        title = bill.get("title", identifier)

        # Extract topics/subjects
        topics = bill.get("subject", [])
        if isinstance(topics, str):
            topics = [topics]

        # Get classification (bill type)
        classification = bill.get("classification", [])
        if classification:
            topics = classification + topics

        return {
            "source": "openstates",
            "external_id": external_id,
            "title": title,
            "level": "state",
            "status": status,
            "introduced_at": introduced_at,
            "topic_tags": [t for t in topics if t][:10],  # Limit to 10 tags
            "canonical_key": f"us:az:{session}:{identifier}".lower(),
        }

    def _map_status(self, bill: Dict) -> str:
        """Map bill data to status enum."""
        # Check latest action
        latest_action = bill.get("latest_action_description", "").lower()

        if "passed" in latest_action or "signed" in latest_action:
            return "passed"
        elif "failed" in latest_action or "vetoed" in latest_action:
            return "failed"
        elif "committee" in latest_action:
            return "in_committee"
        elif "introduced" in latest_action or "read" in latest_action:
            return "introduced"
        elif "calendar" in latest_action or "scheduled" in latest_action:
            return "scheduled"
        elif "tabled" in latest_action or "held" in latest_action:
            return "tabled"
        elif "withdrawn" in latest_action:
            return "withdrawn"
        else:
            return "unknown"

    def _get_bill_url(self, bill: Dict) -> str:
        """Get the official URL for a bill."""
        # Check for openstates_url first
        openstates_url = bill.get("openstates_url")
        if openstates_url:
            return openstates_url

        # Check sources
        sources = bill.get("sources", [])
        for source in sources:
            url = source.get("url")
            if url:
                return url

        # Fallback to constructed URL
        identifier = bill.get("identifier", "")
        session = bill.get("session", "")
        return f"https://www.azleg.gov/legtext/{session}/{identifier}.htm"

    async def _get_or_create_connector(self) -> Connector:
        """Get or create the Arizona connector record."""
        result = await self.db.execute(
            select(Connector).where(Connector.name == "arizona")
        )
        connector = result.scalar_one_or_none()

        if not connector:
            connector = Connector(
                name="arizona",
                source="openstates",
                enabled=True,
                config={
                    "base_url": OPENSTATES_API_BASE,
                    "jurisdiction": "Arizona",
                }
            )
            self.db.add(connector)
            await self.db.flush()

        return connector

    async def run(self, limit: int = 50, pages: int = 1) -> Dict[str, Any]:
        """
        Run the Arizona connector to fetch and store bills.

        Args:
            limit: Maximum number of bills per page
            pages: Number of pages to fetch

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
            for page in range(1, pages + 1):
                # Fetch bills
                bills = await self.get_recent_bills(limit=limit, page=page)
                stats["bills_fetched"] += len(bills)
                logger.info(f"Fetched {len(bills)} Arizona bills (page {page})")

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
                            bill_url = self._get_bill_url(bill)
                            source = MeasureSource(
                                measure_id=measure.id,
                                label="Arizona Legislature",
                                url=bill_url,
                                ctype="html",
                                is_primary=True
                            )
                            self.db.add(source)

                            stats["new_measures"] += 1

                    except Exception as e:
                        logger.error(f"Error processing bill {bill.get('identifier')}: {e}")
                        stats["errors"] += 1

            # Update run status
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            run.stats = stats

            await self.db.commit()
            logger.info(f"Arizona connector completed: {stats}")

        except Exception as e:
            logger.error(f"Arizona connector failed: {e}")
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(e)
            run.stats = stats
            await self.db.commit()
            raise

        return stats


async def run_arizona_connector(db: AsyncSession, limit: int = 50, pages: int = 1) -> Dict[str, Any]:
    """
    Convenience function to run the Arizona connector.

    Usage:
        from app.connectors.arizona import run_arizona_connector
        stats = await run_arizona_connector(db, limit=50, pages=2)
    """
    connector = ArizonaConnector(db)
    return await connector.run(limit=limit, pages=pages)
