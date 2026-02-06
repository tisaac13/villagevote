"""
Monitoring and error tracking for CivicSwipe

Integrates with Sentry for error tracking and provides custom metrics.
"""
import logging
from typing import Optional, Dict, Any
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry for error tracking."""
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=f"civicswipe-api@{settings.VERSION}",
            traces_sample_rate=0.1 if settings.ENVIRONMENT == 'production' else 1.0,
            profiles_sample_rate=0.1 if settings.ENVIRONMENT == 'production' else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            # Don't send PII
            send_default_pii=False,
            # Filter out health check transactions
            before_send_transaction=_filter_transactions,
        )

        logger.info("Sentry initialized successfully")

    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def _filter_transactions(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Filter out noisy transactions."""
    # Don't track health check endpoints
    transaction = event.get('transaction', '')
    if '/health' in transaction:
        return None
    return event


def capture_exception(error: Exception, extra: Optional[Dict[str, Any]] = None) -> None:
    """Capture an exception to Sentry."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass


def capture_message(message: str, level: str = 'info', extra: Optional[Dict[str, Any]] = None) -> None:
    """Capture a message to Sentry."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        pass


def set_user_context(user_id: str, email: Optional[str] = None) -> None:
    """Set user context for error tracking."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        sentry_sdk.set_user({
            'id': user_id,
            'email': email,
        })
    except ImportError:
        pass


def track_task(task_name: str):
    """Decorator to track Celery task execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Task started: {task_name}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Task completed: {task_name}")
                return result
            except Exception as e:
                logger.error(f"Task failed: {task_name} - {e}")
                capture_exception(e, extra={'task_name': task_name})
                raise
        return wrapper
    return decorator


# Simple in-memory metrics (replace with Prometheus/StatsD in production)
class Metrics:
    """Simple metrics collection."""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, tags)
        self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, tags)
        self._gauges[key] = value

    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Get a counter value."""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0)

    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get a gauge value."""
        key = self._make_key(name, tags)
        return self._gauges.get(key, 0.0)

    def get_all(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            'counters': self._counters.copy(),
            'gauges': self._gauges.copy(),
        }

    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key for a metric."""
        if not tags:
            return name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


# Global metrics instance
metrics = Metrics()


# Track common operations
def track_api_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Track an API request."""
    metrics.increment('api.requests.total', tags={'method': method, 'status': str(status_code)})
    metrics.gauge('api.request.duration_ms', duration_ms, tags={'method': method, 'path': path})


def track_vote(level: str) -> None:
    """Track a vote."""
    metrics.increment('votes.total', tags={'level': level})


def track_measure_ingestion(source: str, count: int) -> None:
    """Track measure ingestion."""
    metrics.increment('measures.ingested', value=count, tags={'source': source})


def track_summarization(success: bool) -> None:
    """Track a summarization."""
    status = 'success' if success else 'failure'
    metrics.increment('summarization.total', tags={'status': status})
