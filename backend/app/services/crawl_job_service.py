import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.crawl_job import crawl_job_crud
from app.models.competitor import Competitor
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job_schema import CrawlJobPublic, CreateCrawlJobSchema
from app.crawlers import CrawlerRegistry
from app.crawlers.base import CrawlerError
from app.core.config import settings
from app.services.competitor_cache_service import CompetitorCacheService
from app.services.competitor_price_service import CompetitorPriceConflictError, CompetitorPriceService
from app.schemas.competitor_price_schema import CreateCompetitorPriceSchema

logger = logging.getLogger(__name__)


class CrawlJobServiceError(Exception):
    pass


class CrawlJobNotFoundError(CrawlJobServiceError):
    pass


class CrawlJobConflictError(CrawlJobServiceError):
    pass


class CrawlJobValidationError(CrawlJobServiceError):
    pass


class CrawlJobService:
    ALLOWED_TRANSITIONS = {
        "pending": {"running", "failed"},
        "running": {"completed", "failed"},
        "completed": set(),
        "failed": set(),
    }

    def __init__(self, db: Session, registry: CrawlerRegistry | None = None,
                 cache_service: CompetitorCacheService | None = None,
                 request_delay_seconds: float | None = None) -> None:
        self.db = db
        self.crud = crawl_job_crud
        self.registry = registry or CrawlerRegistry()
        self.cache = cache_service
        self.request_delay_seconds = settings.crawler_request_delay_seconds if request_delay_seconds is None else request_delay_seconds

    def get(self, job_id: UUID) -> CrawlJobPublic:
        return CrawlJobPublic.model_validate(self._get_model(job_id))

    def list(self, *, skip: int = 0, limit: int = 100) -> list[CrawlJobPublic]:
        if skip < 0 or not 1 <= limit <= 1000:
            raise CrawlJobValidationError("Invalid pagination values")
        return [CrawlJobPublic.model_validate(item) for item in self.crud.get_all(self.db, 
        skip=skip, limit=limit)]

    def create(self, job_in: CreateCrawlJobSchema) -> CrawlJobPublic:
        competitor = self.db.get(Competitor, job_in.competitor_id)
        if competitor is None:
            raise CrawlJobValidationError(
                f"Competitor {job_in.competitor_id} does not exist")
        if not getattr(competitor, "is_active", True):
            raise CrawlJobValidationError(
                "Cannot create a crawl job for an inactive competitor")

        data = job_in.model_dump()
        data.setdefault("status", "pending")
        data.setdefault("records_collected", 0)
        job = CrawlJob(**data)

        try:
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
        except IntegrityError as exc:
            self.db.rollback()
            raise CrawlJobConflictError("Crawl job could not be created") from exc

        return CrawlJobPublic.model_validate(job)

    def start(self, job_id: UUID) -> CrawlJobPublic:
        job = self._get_model(job_id)
        self._transition(job, "running")
        job.started_at = datetime.now(timezone.utc)
        return self._save(job)

    def complete(self, job_id: UUID, *, records_collected: int) -> CrawlJobPublic:
        if records_collected < 0:
            raise CrawlJobValidationError(
                "records_collected cannot be negative")
        job = self._get_model(job_id)
        self._transition(job, "completed")
        job.records_collected = records_collected
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = None
        return self._save(job)

    def fail(self, job_id: UUID, *, error_message: str) -> CrawlJobPublic:
        message = error_message.strip()
        if not message:
            raise CrawlJobValidationError(
                "error_message is required for a failed job")
        job = self._get_model(job_id)
        self._transition(job, "failed")
        job.error_message = message
        job.completed_at = datetime.now(timezone.utc)
        return self._save(job)

    async def crawl_competitor(self, competitor_id: UUID) -> CrawlJobPublic:
        """Crawl active mappings with per-observation commits and isolated failures."""
        created = self.create(CreateCrawlJobSchema(competitor_id=competitor_id))
        self.start(created.job_id)
        mappings = self.db.get(Competitor, competitor_id).competitor_product
        mappings = [mapping for mapping in mappings if getattr(mapping, "is_active", True)]
        crawler = self.registry.get(competitor_id)
        price_service = CompetitorPriceService(self.db)
        successes = 0
        failures: list[str] = []

        for index, mapping in enumerate(mappings):
            if index and self.request_delay_seconds > 0:
                await asyncio.sleep(self.request_delay_seconds)
            try:
                result = await crawler.crawl_product(mapping)
                await price_service.record(CreateCompetitorPriceSchema(
                    competitor_product_id=mapping.competitor_product_id,
                    crawl_job_id=created.job_id,
                    competitor_price=result.price,
                    stock_qty=result.stock_qty,
                    in_stock=result.in_stock,
                    crawl_timestamp=datetime.now(timezone.utc),
                ))
                successes += 1
                if self.cache is not None:
                    await self.cache.invalidate_price_inputs(
                        product_id=mapping.product_id,
                        competitor_id=competitor_id,
                        mapping_id=mapping.competitor_product_id,
                    )
            except (CrawlerError, CompetitorPriceConflictError) as exc:
                message = f"{mapping.competitor_product_id}: {exc}"
                failures.append(message)
                self._record_mapping_error(mapping, str(exc))
                logger.warning("Competitor mapping crawl failed: %s", message)
            except Exception as exc:
                message = f"{mapping.competitor_product_id}: unexpected crawler failure"
                failures.append(message)
                self._record_mapping_error(mapping, "Unexpected crawler failure")
                logger.exception("Competitor mapping crawl failed", exc_info=exc)

        if successes:
            return self.complete(created.job_id, records_collected=successes)
        detail = "; ".join(failures) if failures else "No active competitor-product mappings"
        job = self._get_model(created.job_id)
        job.records_collected = 0
        return self.fail(created.job_id, error_message=detail[:2000])

    def _record_mapping_error(self, mapping, message: str) -> None:
        try:
            mapping.last_crawled_at = datetime.now(timezone.utc)
            mapping.last_crawl_error = message[:2000]
            self.db.add(mapping)
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Could not update failed crawl metadata for mapping %s", mapping.competitor_product_id)

    def _transition(self, job: CrawlJob, new_status: str) -> None:
        current_status = getattr(job.status, "value", job.status)
        if new_status not in self.ALLOWED_TRANSITIONS.get(current_status, set()):
            raise CrawlJobValidationError(
                f"Invalid crawl job transition: {current_status} -> {new_status}")
        job.status = new_status

    def _save(self, job: CrawlJob) -> CrawlJobPublic:
        try:
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
        except IntegrityError as exc:
            self.db.rollback()
            raise CrawlJobConflictError("Crawl job could not be updated") from exc
        return CrawlJobPublic.model_validate(job)

    def _get_model(self, job_id: UUID) -> CrawlJob:
        job = self.crud.get(self.db, job_id)
        if job is None:
            raise CrawlJobNotFoundError(
                f"Crawl job {job_id} was not found")
        return job
