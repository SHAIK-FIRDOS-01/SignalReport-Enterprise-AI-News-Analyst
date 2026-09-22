import asyncio
import logging
from typing import List, Optional

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services.gnews_client import GNewsClient
from app.services.article_repository import ArticleRepository

logger = logging.getLogger("scheduler")

# Standard news categories polled every cycle (4 requests/cycle * 12 cycles = 48 requests/day)
POLLING_CATEGORIES: List[str] = ["nation", "business", "technology", "general"]
_scheduler_task: Optional[asyncio.Task] = None


async def run_polling_cycle(
    client: Optional[GNewsClient] = None,
    session_factory=None,
) -> int:
    """
    Executes a single polling cycle across all designated news categories.
    Catches exceptions per category so a single failure never aborts remaining categories.
    Returns the total number of articles successfully ingested.
    """
    gnews_client = client or GNewsClient()
    db_factory = session_factory or AsyncSessionLocal

    total_ingested = 0
    logger.info("Starting rolling news ingestion cycle...")

    for category in POLLING_CATEGORIES:
        try:
            logger.info(f"Polling category '{category}' from upstream news source...")
            articles = await gnews_client.fetch_top_headlines(category=category)
            if articles:
                async with db_factory() as session:
                    count = await ArticleRepository.batch_insert_async(
                        session=session,
                        articles=articles,
                        category=category,
                    )
                    total_ingested += count
                    logger.info(f"Category '{category}': {count} articles ingested.")
            else:
                logger.info(f"Category '{category}': 0 articles returned from upstream.")
        except Exception as exc:
            logger.error(
                f"Error during polling cycle for category '{category}': {exc}",
                exc_info=True,
            )

    logger.info(f"Rolling news ingestion cycle completed. Total articles processed: {total_ingested}")
    return total_ingested


async def polling_loop(interval_seconds: Optional[int] = None) -> None:
    """
    Continuous background loop that runs periodic news ingestion cycles every 2 hours
    (or configured interval) with an error boundary and graceful shutdown support.
    """
    if interval_seconds is not None:
        delay = interval_seconds
    else:
        try:
            settings = get_settings()
            delay = settings.POLLING_INTERVAL_HOURS * 3600
        except Exception:
            delay = 7200
    logger.info(f"Background rolling news poller started. Interval: {delay}s ({delay / 3600:.1f} hours).")

    try:
        while True:
            try:
                await run_polling_cycle()
            except Exception as exc:
                logger.error(f"Unhandled error in rolling news cycle error boundary: {exc}", exc_info=True)

            logger.info(f"Scheduler sleeping for {delay} seconds until next cycle...")
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        logger.info("Background rolling news poller received cancellation request. Shutting down cleanly.")
        raise


def start_scheduler(interval_seconds: Optional[int] = None) -> asyncio.Task:
    """
    Initializes and starts the background scheduler task.
    """
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(polling_loop(interval_seconds=interval_seconds))
        logger.info("Created background scheduler task.")
    return _scheduler_task


async def stop_scheduler() -> None:
    """
    Gracefully halts the background scheduler task on application teardown.
    """
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.info("Cancelling background scheduler task...")
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
        logger.info("Background scheduler task successfully terminated.")
