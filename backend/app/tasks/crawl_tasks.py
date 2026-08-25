from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.redis import RedisClient
from app.models.competitor import Competitor
from app.services.competitor_cache_service import CompetitorCacheService
from app.services.crawl_job_service import CrawlJobService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _execute(job_id: UUID) -> dict:
    cache_client = RedisClient()
    cache = None
    try:
        await cache_client.connect()
        cache = CompetitorCacheService(cache_client)
    except Exception:
        logger.warning("Worker could not connect to the cache; crawl will continue", exc_info=True)

    db = SessionLocal()
    try:
        result = await CrawlJobService(db, cache_service=cache).execute_job(job_id)
        return result.model_dump(mode="json")
    finally:
        db.close()
        await cache_client.close()


@celery_app.task(name="app.tasks.execute_competitor_crawl")
def execute_competitor_crawl(job_id: str) -> dict:
    """Run one previously-created crawl job in a worker-owned session."""
    return asyncio.run(_execute(UUID(job_id)))


@celery_app.task(name="app.tasks.enqueue_scheduled_competitor_crawls")
def enqueue_scheduled_competitor_crawls() -> dict[str, int]:
    """Create and dispatch jobs; Beat never performs crawler work itself."""
    db = SessionLocal()
    try:
        competitor_ids = list(db.scalars(
            select(Competitor.competitor_id).where(Competitor.is_active.is_(True))
        ).all())
        service = CrawlJobService(db)
        enqueued = 0
        failures = 0
        for competitor_id in competitor_ids:
            try:
                _, created = service.enqueue_competitor(competitor_id)
                enqueued += int(created)
            except Exception:
                failures += 1
                logger.exception("Could not schedule crawl for competitor %s", competitor_id)
        return {"competitors": len(competitor_ids), "enqueued": enqueued, "failures": failures}
    finally:
        db.close()
