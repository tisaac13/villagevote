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
def ingest_federal_data(self, congress: int = 118, limit: int = 50) -> Dict[str, Any]:
    """
    Ingest federal legislation data from Congress.gov.

    Args:
        congress: Congress number (default: 118)
        limit: Maximum bills to fetch

    Returns:
        Ingestion statistics
    """
    logger.info(f"Starting federal data ingestion (congress={congress}, limit={limit})")

    async def _run():
        from app.connectors.federal import run_federal_connector
        async with async_session_maker() as db:
            stats = await run_federal_connector(db, congress=congress, limit=limit)
            return stats

    try:
        stats = run_async(_run())
        logger.info(f"Federal ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Federal ingestion failed: {e}")
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
        results["federal"] = ingest_federal_data(congress=118, limit=100)
    except Exception as e:
        logger.error(f"Federal ingestion failed: {e}")
        results["federal"] = {"error": str(e)}

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
