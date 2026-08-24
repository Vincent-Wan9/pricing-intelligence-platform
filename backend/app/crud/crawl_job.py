from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job_schema import CreateCrawlJobSchema, UpdateCrawlJobSchema


class CrawlJobCRUD(CRUDBase[CrawlJob, CreateCrawlJobSchema, UpdateCrawlJobSchema]):

    def get_by_competitor(self, db: Session, competitor_id: UUID):
        stmt = (select(CrawlJob).where(CrawlJob.competitor_id == competitor_id)
            .order_by(CrawlJob.started_at.desc()))

        return list(db.scalars(stmt).all())

    def get_latest_job(self, db: Session, competitor_id: UUID):
        stmt = (select(CrawlJob).where(CrawlJob.competitor_id == competitor_id)
            .order_by(CrawlJob.started_at.desc())
            .limit(1))

        return db.scalar(stmt)

    def get_active_job(self, db: Session, competitor_id: UUID):
        stmt = (select(CrawlJob).where(
            CrawlJob.competitor_id == competitor_id,
            CrawlJob.status.in_(("pending", "running")),
        ).order_by(CrawlJob.started_at.desc()).limit(1))
        return db.scalar(stmt)

    def get_for_update(self, db: Session, job_id: UUID):
        return db.scalar(select(CrawlJob).where(CrawlJob.job_id == job_id).with_for_update())

    def get_by_status(self, db: Session, status: str):
        stmt = (select(CrawlJob).where(CrawlJob.status == status)
            .order_by(CrawlJob.started_at.desc()))

        return list(db.scalars(stmt).all())

    def get_failed_jobs(self, db: Session):
        stmt = (select(CrawlJob).where(CrawlJob.status == "failed")
            .order_by(CrawlJob.started_at.desc()))

        return list(db.scalars(stmt).all())


crawl_job_crud = CrawlJobCRUD(CrawlJob)
