"""
Phoenix Legistar Connector

Fetches city council meetings, agendas, and votes from Phoenix Legistar.
Legistar is a legislative management system used by many municipalities.

This connector:
- Fetches upcoming city council meetings
- Parses agenda items from meeting details
- Extracts voting outcomes when available
- Maps data to the CivicSwipe schema
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import logging
import re
from bs4 import BeautifulSoup

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models import Measure, MeasureSource, MeasureStatusEvent, Connector, IngestionRun

logger = logging.getLogger(__name__)

# Phoenix Legistar base URL
LEGISTAR_BASE_URL = "https://phoenix.legistar.com"

# Legistar Web API (if available) or fallback to scraping
LEGISTAR_API_BASE = "https://webapi.legistar.com/v1/phoenix"


class PhoenixLegistarConnector:
    """
    Connector for fetching Phoenix City Council data from Legistar.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_url = settings.PHOENIX_LEGISTAR_BASE_URL or LEGISTAR_BASE_URL

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    async def _fetch_api(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch data from Legistar Web API."""
        try:
            url = f"{LEGISTAR_API_BASE}{endpoint}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching API {endpoint}: {e}")
            return None

    async def get_upcoming_events(self, days: int = 30) -> List[Dict]:
        """
        Fetch upcoming city council events/meetings.

        Args:
            days: Number of days ahead to look for events

        Returns:
            List of event dictionaries
        """
        # Try Legistar Web API first
        try:
            # Calculate date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)

            # Legistar API format: YYYY-MM-DD
            params = {
                "$filter": f"EventDate ge datetime'{start_date.strftime('%Y-%m-%d')}' and EventDate le datetime'{end_date.strftime('%Y-%m-%d')}'",
                "$orderby": "EventDate"
            }

            data = await self._fetch_api("/Events", params)
            if data:
                return data
        except Exception as e:
            logger.warning(f"API fetch failed, falling back to scraping: {e}")

        # Fallback: scrape the calendar page
        return await self._scrape_calendar()

    async def _scrape_calendar(self) -> List[Dict]:
        """Scrape the Legistar calendar page for events."""
        events = []

        try:
            html = await self._fetch_page(f"{self.base_url}/Calendar.aspx")
            if not html:
                return events

            soup = BeautifulSoup(html, 'html.parser')

            # Find event rows in the calendar table
            event_rows = soup.find_all('tr', class_='rgRow') + soup.find_all('tr', class_='rgAltRow')

            for row in event_rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        # Extract event info
                        date_cell = cells[0].get_text(strip=True)
                        name_cell = cells[1].get_text(strip=True)
                        location_cell = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                        # Get link to event details
                        link = cells[1].find('a')
                        event_url = None
                        event_id = None
                        if link and link.get('href'):
                            event_url = f"{self.base_url}/{link.get('href')}"
                            # Extract event ID from URL
                            match = re.search(r'ID=(\d+)', link.get('href'))
                            if match:
                                event_id = match.group(1)

                        events.append({
                            'EventId': event_id,
                            'EventDate': date_cell,
                            'EventBodyName': name_cell,
                            'EventLocation': location_cell,
                            'EventUrl': event_url,
                        })
                except Exception as e:
                    logger.warning(f"Error parsing event row: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping calendar: {e}")

        return events

    async def get_event_items(self, event_id: str) -> List[Dict]:
        """
        Fetch agenda items for a specific event/meeting.

        Args:
            event_id: Legistar event ID

        Returns:
            List of agenda item dictionaries
        """
        # Try API first
        try:
            data = await self._fetch_api(f"/Events/{event_id}/EventItems")
            if data:
                return data
        except Exception as e:
            logger.warning(f"API fetch failed for event items: {e}")

        # Fallback to scraping
        return await self._scrape_event_items(event_id)

    async def _scrape_event_items(self, event_id: str) -> List[Dict]:
        """Scrape agenda items from event detail page."""
        items = []

        try:
            url = f"{self.base_url}/MeetingDetail.aspx?ID={event_id}"
            html = await self._fetch_page(url)
            if not html:
                return items

            soup = BeautifulSoup(html, 'html.parser')

            # Find agenda items table
            item_rows = soup.find_all('tr', class_='rgRow') + soup.find_all('tr', class_='rgAltRow')

            for row in item_rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        # Extract item info
                        number = cells[0].get_text(strip=True)
                        title = cells[1].get_text(strip=True)

                        # Get action/result if available
                        action = ""
                        if len(cells) > 2:
                            action = cells[-1].get_text(strip=True)

                        # Get link to matter details
                        link = cells[1].find('a')
                        matter_url = None
                        matter_id = None
                        if link and link.get('href'):
                            matter_url = f"{self.base_url}/{link.get('href')}"
                            match = re.search(r'ID=(\d+)', link.get('href'))
                            if match:
                                matter_id = match.group(1)

                        items.append({
                            'EventItemId': f"{event_id}-{number}",
                            'EventItemAgendaNumber': number,
                            'EventItemTitle': title,
                            'EventItemActionName': action,
                            'EventItemMatterId': matter_id,
                            'EventItemMatterUrl': matter_url,
                        })
                except Exception as e:
                    logger.warning(f"Error parsing agenda item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping event items: {e}")

        return items

    def _map_event_to_measure(self, event: Dict, item: Dict) -> Dict:
        """
        Map Legistar event/item to CivicSwipe Measure schema.

        Args:
            event: Event data
            item: Agenda item data

        Returns:
            Dictionary ready for Measure creation
        """
        # Build external ID
        event_id = event.get('EventId', 'unknown')
        item_id = item.get('EventItemId', item.get('EventItemAgendaNumber', 'unknown'))
        external_id = f"phoenix-{event_id}-{item_id}"

        # Get title
        title = item.get('EventItemTitle', 'Untitled Agenda Item')
        if len(title) > 500:
            title = title[:497] + "..."

        # Map status based on action
        # Map status based on action (handle None values)
        action = item.get('EventItemActionName') or ''
        status = self._map_status(action)

        # Get scheduled date
        scheduled_for = None
        event_date = event.get('EventDate')
        if event_date:
            try:
                if isinstance(event_date, str):
                    # Try various date formats
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            scheduled_for = datetime.strptime(event_date.split()[0], fmt)
                            break
                        except ValueError:
                            continue
                elif isinstance(event_date, datetime):
                    scheduled_for = event_date
            except Exception as e:
                logger.warning(f"Error parsing date {event_date}: {e}")

        # Build topic tags
        body_name = event.get('EventBodyName') or ''
        topics = []
        if body_name and 'council' in body_name.lower():
            topics.append('city council')
        if body_name and 'planning' in body_name.lower():
            topics.append('planning')
        if body_name and 'zoning' in body_name.lower():
            topics.append('zoning')

        return {
            "source": "legistar",
            "external_id": external_id,
            "title": title,
            "level": "city",
            "status": status,
            "scheduled_for": scheduled_for,
            "topic_tags": topics[:10],
            "canonical_key": f"us:az:phoenix:{external_id}",
        }

    def _map_status(self, action: Optional[str]) -> str:
        """Map action text to status enum."""
        if not action:
            return "scheduled"
        action_lower = action.lower()

        if 'approved' in action_lower or 'passed' in action_lower or 'adopted' in action_lower:
            return "passed"
        elif 'denied' in action_lower or 'rejected' in action_lower or 'failed' in action_lower:
            return "failed"
        elif 'tabled' in action_lower or 'continued' in action_lower or 'postponed' in action_lower:
            return "tabled"
        elif 'withdrawn' in action_lower:
            return "withdrawn"
        elif action_lower:
            return "scheduled"
        else:
            return "scheduled"

    async def _get_or_create_connector(self) -> Connector:
        """Get or create the Phoenix Legistar connector record."""
        result = await self.db.execute(
            select(Connector).where(Connector.name == "phoenix_legistar")
        )
        connector = result.scalar_one_or_none()

        if not connector:
            connector = Connector(
                name="phoenix_legistar",
                source="legistar",
                enabled=True,
                config={
                    "base_url": self.base_url,
                    "city": "Phoenix",
                    "state": "AZ",
                }
            )
            self.db.add(connector)
            await self.db.flush()

        return connector

    async def run(self, days: int = 30, max_events: int = 10) -> Dict[str, Any]:
        """
        Run the Phoenix Legistar connector to fetch and store agenda items.

        Args:
            days: Number of days ahead to look for events
            max_events: Maximum number of events to process

        Returns:
            Statistics about the ingestion run
        """
        stats = {
            "events_fetched": 0,
            "items_fetched": 0,
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
            # Fetch upcoming events
            events = await self.get_upcoming_events(days=days)
            events = events[:max_events]  # Limit events
            stats["events_fetched"] = len(events)
            logger.info(f"Fetched {len(events)} Phoenix events")

            for event in events:
                try:
                    event_id = event.get('EventId')
                    if not event_id:
                        continue

                    # Fetch agenda items for this event
                    items = await self.get_event_items(event_id)
                    stats["items_fetched"] += len(items)

                    for item in items:
                        try:
                            # Map to measure schema
                            measure_data = self._map_event_to_measure(event, item)

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
                                source_url = item.get('EventItemMatterUrl') or event.get('EventUrl') or f"{self.base_url}/MeetingDetail.aspx?ID={event_id}"
                                source = MeasureSource(
                                    measure_id=measure.id,
                                    label="Phoenix Legistar",
                                    url=source_url,
                                    ctype="html",
                                    is_primary=True
                                )
                                self.db.add(source)

                                stats["new_measures"] += 1

                        except Exception as e:
                            logger.error(f"Error processing agenda item: {e}")
                            stats["errors"] += 1

                except Exception as e:
                    logger.error(f"Error processing event {event.get('EventId')}: {e}")
                    stats["errors"] += 1

            # Update run status
            run.status = "succeeded"
            run.finished_at = datetime.utcnow()
            run.stats = stats

            await self.db.commit()
            logger.info(f"Phoenix Legistar connector completed: {stats}")

        except Exception as e:
            logger.error(f"Phoenix Legistar connector failed: {e}")
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(e)
            run.stats = stats
            await self.db.commit()
            raise

        return stats


async def run_phoenix_connector(db: AsyncSession, days: int = 30, max_events: int = 10) -> Dict[str, Any]:
    """
    Convenience function to run the Phoenix Legistar connector.

    Usage:
        from app.connectors.phoenix_legistar import run_phoenix_connector
        stats = await run_phoenix_connector(db, days=30, max_events=5)
    """
    connector = PhoenixLegistarConnector(db)
    return await connector.run(days=days, max_events=max_events)
