"""
Summarization tasks

These tasks run periodically to generate AI summaries for new measures.
"""
import logging
from typing import Dict, Any
import asyncio
from uuid import UUID

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


@celery_app.task(bind=True, name="app.tasks.summarization.summarize_pending_measures")
def summarize_pending_measures(self, limit: int = 20) -> Dict[str, Any]:
    """
    Summarize measures that don't have summaries yet.

    Args:
        limit: Maximum number of measures to summarize

    Returns:
        Summarization statistics
    """
    logger.info(f"Starting batch summarization (limit={limit})")

    async def _run():
        from app.services.summarizer import summarize_measures
        async with async_session_maker() as db:
            stats = await summarize_measures(db, limit=limit)
            return stats

    try:
        stats = run_async(_run())
        logger.info(f"Batch summarization completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Batch summarization failed: {e}")
        raise self.retry(exc=e, countdown=120, max_retries=2)


@celery_app.task(bind=True, name="app.tasks.summarization.summarize_single_measure")
def summarize_single_measure(self, measure_id: str, full_text: str = None) -> bool:
    """
    Summarize a single measure by ID.

    Args:
        measure_id: UUID of the measure to summarize
        full_text: Optional full text of the measure

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting single measure summarization: {measure_id}")

    async def _run():
        from app.services.summarizer import summarization_service
        async with async_session_maker() as db:
            result = await summarization_service.summarize_and_update(
                db=db,
                measure_id=UUID(measure_id),
                full_text=full_text
            )
            return result

    try:
        result = run_async(_run())
        logger.info(f"Single measure summarization completed: {measure_id} -> {result}")
        return result
    except Exception as e:
        logger.error(f"Single measure summarization failed: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)
