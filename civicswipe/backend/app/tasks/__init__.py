"""
Celery tasks for background job processing
"""
from app.tasks.celery_app import celery_app
from app.tasks.ingestion import (
    ingest_federal_data,
    ingest_arizona_data,
    ingest_phoenix_data,
    ingest_all_sources,
)
from app.tasks.summarization import (
    summarize_pending_measures,
    summarize_single_measure,
)

__all__ = [
    "celery_app",
    "ingest_federal_data",
    "ingest_arizona_data",
    "ingest_phoenix_data",
    "ingest_all_sources",
    "summarize_pending_measures",
    "summarize_single_measure",
]
