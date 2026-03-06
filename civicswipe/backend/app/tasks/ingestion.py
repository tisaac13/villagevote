"""
Data ingestion tasks

These tasks run periodically to fetch legislative data from external sources.
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


@celery_app.task(bind=True, name="app.tasks.ingestion.ingest_federal_data")
def ingest_federal_data(self, congress: int = 119, limit: int = 50, fetch_all: bool = False) -> Dict[str, Any]:
    """
    Ingest federal legislation data from Congress.gov.

    Args:
        congress: Congress number (default: 119)
        limit: Maximum bills to fetch per page
        fetch_all: If True, paginate through ALL bills

    Returns:
        Ingestion statistics
    """
    logger.info(f"Starting federal data ingestion (congress={congress}, limit={limit}, fetch_all={fetch_all})")

    async def _run():
        from app.connectors.federal import run_federal_connector
        async with async_session_maker() as db:
            stats = await run_federal_connector(db, congress=congress, limit=limit, fetch_all=fetch_all)
            return stats

    try:
        stats = run_async(_run())
        logger.info(f"Federal ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Federal ingestion failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.ingestion.ingest_roll_call_votes")
def ingest_roll_call_votes(self, congress: int = 119, session: int = 1) -> Dict[str, Any]:
    """
    Ingest roll call votes from House Clerk XML and Senate XML.

    Args:
        congress: Congress number (default: 119)
        session: Session number (1 or 2)

    Returns:
        Combined ingestion statistics
    """
    logger.info(f"Starting roll call vote ingestion (congress={congress}, session={session})")

    async def _run():
        from app.services.roll_call_votes import RollCallVoteService
        async with async_session_maker() as db:
            service = RollCallVoteService(db)
            try:
                house_stats = await service.ingest_house_votes(congress=congress, session=session)
                senate_stats = await service.ingest_senate_votes(congress=congress, session=session)
                await db.commit()
                return {
                    "house": house_stats,
                    "senate": senate_stats,
                }
            finally:
                await service.close()

    try:
        stats = run_async(_run())
        logger.info(f"Roll call vote ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Roll call vote ingestion failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.ingestion.ingest_arizona_data")
def ingest_arizona_data(self, limit: int = 50, pages: int = 1) -> Dict[str, Any]:
    """
    Ingest Arizona state legislation data from Open States.

    Args:
        limit: Maximum bills per page
        pages: Number of pages to fetch

    Returns:
        Ingestion statistics
    """
    logger.info(f"Starting Arizona data ingestion (limit={limit}, pages={pages})")

    async def _run():
        from app.connectors.arizona import run_arizona_connector
        async with async_session_maker() as db:
            stats = await run_arizona_connector(db, limit=limit, pages=pages)
            return stats

    try:
        stats = run_async(_run())
        logger.info(f"Arizona ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Arizona ingestion failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.ingestion.ingest_phoenix_data")
def ingest_phoenix_data(self, days: int = 30, max_events: int = 10) -> Dict[str, Any]:
    """
    Ingest Phoenix city council data from Legistar.

    Args:
        days: Number of days ahead to look for events
        max_events: Maximum events to process

    Returns:
        Ingestion statistics
    """
    logger.info(f"Starting Phoenix data ingestion (days={days}, max_events={max_events})")

    async def _run():
        from app.connectors.phoenix_legistar import run_phoenix_connector
        async with async_session_maker() as db:
            stats = await run_phoenix_connector(db, days=days, max_events=max_events)
            return stats

    try:
        stats = run_async(_run())
        logger.info(f"Phoenix ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Phoenix ingestion failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


# Mapping from connector name to ingestion function
# Used by run_connector to dispatch manual ingestion runs
CONNECTOR_TASK_MAP = {
    "congress": lambda: ingest_federal_data(congress=119, limit=250, fetch_all=True),
    "federal": lambda: ingest_federal_data(congress=119, limit=250, fetch_all=True),
    "roll_call_votes": lambda: ingest_roll_call_votes(congress=119, session=1),
    "arizona": lambda: ingest_arizona_data(limit=50, pages=2),
    "phoenix_legistar": lambda: ingest_phoenix_data(days=14, max_events=10),
    "phoenix": lambda: ingest_phoenix_data(days=14, max_events=10),
}


@celery_app.task(bind=True, name="app.tasks.ingestion.run_connector")
def run_connector(self, run_id: str, connector_name: str) -> Dict[str, Any]:
    """
    Run a specific connector by name and update the IngestionRun record.

    Dispatches to the appropriate ingestion function based on connector name,
    then updates the IngestionRun with results or error.

    Args:
        run_id: UUID string of the IngestionRun record
        connector_name: Name of the connector to run

    Returns:
        Ingestion statistics
    """
    logger.info(f"Starting connector run {run_id} for '{connector_name}'")

    task_fn = CONNECTOR_TASK_MAP.get(connector_name)
    if not task_fn:
        # Update run as failed and bail
        async def _fail():
            from app.models import IngestionRun
            from datetime import datetime, timezone
            async with async_session_maker() as db:
                run = await db.get(IngestionRun, run_id)
                if run:
                    run.status = "failed"
                    run.error = f"Unknown connector: '{connector_name}'"
                    run.finished_at = datetime.now(timezone.utc)
                    await db.commit()

        run_async(_fail())
        return {"error": f"Unknown connector: '{connector_name}'"}

    try:
        stats = task_fn()

        # Update run as succeeded
        async def _succeed():
            from app.models import IngestionRun
            from datetime import datetime, timezone
            async with async_session_maker() as db:
                run = await db.get(IngestionRun, run_id)
                if run:
                    run.status = "succeeded"
                    run.stats = stats or {}
                    run.finished_at = datetime.now(timezone.utc)
                    await db.commit()

        run_async(_succeed())
        logger.info(f"Connector run {run_id} completed: {stats}")
        return stats

    except Exception as e:
        # Update run as failed
        async def _error():
            from app.models import IngestionRun
            from datetime import datetime, timezone
            async with async_session_maker() as db:
                run = await db.get(IngestionRun, run_id)
                if run:
                    run.status = "failed"
                    run.error = str(e)
                    run.finished_at = datetime.now(timezone.utc)
                    await db.commit()

        run_async(_error())
        logger.error(f"Connector run {run_id} failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="app.tasks.ingestion.ingest_all_sources")
def ingest_all_sources(self) -> Dict[str, Dict[str, Any]]:
    """
    Run all data ingestion tasks sequentially.

    Returns:
        Dictionary with statistics from all sources
    """
    logger.info("Starting full data ingestion from all sources")

    results = {}

    # Federal
    try:
        results["federal"] = ingest_federal_data(congress=119, limit=250, fetch_all=True)
    except Exception as e:
        logger.error(f"Federal ingestion failed: {e}")
        results["federal"] = {"error": str(e)}

    # Roll call votes (House + Senate)
    try:
        results["roll_call_votes"] = ingest_roll_call_votes(congress=119, session=1)
    except Exception as e:
        logger.error(f"Roll call vote ingestion failed: {e}")
        results["roll_call_votes"] = {"error": str(e)}

    # Arizona
    try:
        results["arizona"] = ingest_arizona_data(limit=50, pages=2)
    except Exception as e:
        logger.error(f"Arizona ingestion failed: {e}")
        results["arizona"] = {"error": str(e)}

    # Phoenix
    try:
        results["phoenix"] = ingest_phoenix_data(days=14, max_events=10)
    except Exception as e:
        logger.error(f"Phoenix ingestion failed: {e}")
        results["phoenix"] = {"error": str(e)}

    logger.info(f"Full ingestion completed: {results}")
    return results
