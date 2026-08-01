from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.crawl_job import crawl_job_crud
from app.models.competitor import Competitor
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job_schema import CrawlJobPublic, CreateCrawlJobSchema


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

    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = crawl_job_crud

    def get(self, job_id: UUID) -> CrawlJobPublic:
        return CrawlJobPublic.model_validate(self._get_model(job_id))

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
