from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from app.dependencies import CrawlJobServiceDep, require_roles
from app.core.config import settings
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job_schema import CompleteCrawlJobSchema, CrawlJobPublic, CrawlSchedulePublic, CreateCrawlJobSchema, FailCrawlJobSchema

router=APIRouter(prefix = "/crawl-jobs", tags = ["crawl jobs"])
read=Depends(require_roles("viewer", "editor", "approver", "admin"))
write=Depends(require_roles("editor", "admin"))


@router.get("/schedule/status", response_model=CrawlSchedulePublic, dependencies=[read])
def schedule_status(service: CrawlJobServiceDep):
    latest = service.db.scalar(
        select(CrawlJob).where(CrawlJob.completed_at.is_not(None))
        .order_by(CrawlJob.completed_at.desc()).limit(1)
    )
    return CrawlSchedulePublic(
        enabled=settings.competitor_crawl_schedule_seconds > 0,
        interval_seconds=settings.competitor_crawl_schedule_seconds,
        last_crawl_at=latest.completed_at if latest else None,
        # Celery Beat does not persist its next tick in this application.
        next_scheduled_crawl=None,
    )


@router.get("", response_model = list[CrawlJobPublic], dependencies = [read])
def list_items(service: CrawlJobServiceDep, skip: int = Query(0, ge = 0), limit: int = Query(100, ge=1, le=1000)): 
    return service.list(skip = skip, limit = limit)


@router.get("/{job_id}", response_model = CrawlJobPublic, dependencies = [read])
def get_item(job_id: UUID, service: CrawlJobServiceDep): 
    return service.get(job_id)


@router.post("", response_model = CrawlJobPublic, status_code = 201, dependencies = [write])
def create_item(data: CreateCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.create(data)


@router.post("/competitors/{competitor_id}", response_model=CrawlJobPublic, status_code=202, dependencies=[write])
def crawl_competitor(competitor_id: UUID, service: CrawlJobServiceDep):
    job, _ = service.enqueue_competitor(competitor_id)
    return job


@router.post("/{job_id}/start", response_model = CrawlJobPublic, dependencies = [write])
def start(job_id: UUID, service: CrawlJobServiceDep): 
    return service.start(job_id)


@router.post("/{job_id}/complete", response_model = CrawlJobPublic, dependencies = [write])
def complete(job_id: UUID, data: CompleteCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.complete(job_id, records_collected = data.records_collected)


@router.post("/{job_id}/fail", response_model = CrawlJobPublic, dependencies = [write])
def fail(job_id: UUID, data: FailCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.fail(job_id, error_message = data.error_message)
