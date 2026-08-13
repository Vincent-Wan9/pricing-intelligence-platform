from uuid import UUID
from fastapi import APIRouter, Depends, Query
from app.dependencies import CrawlJobServiceDep, require_roles
from app.schemas.crawl_job_schema import CompleteCrawlJobSchema, CrawlJobPublic, CreateCrawlJobSchema, FailCrawlJobSchema

router=APIRouter(prefix = "/crawl-jobs", tags = ["crawl jobs"])
read=Depends(require_roles("viewer", "editor", "approver", "admin"))
write=Depends(require_roles("editor", "admin"))


@router.get("", response_model = list[CrawlJobPublic], dependencies = [read])
def list_items(service: CrawlJobServiceDep, skip: int = Query(0, ge = 0), limit: int = Query(100, ge=1, le=1000)): 
    return service.list(skip = skip, limit = limit)


@router.get("/{job_id}", response_model = CrawlJobPublic, dependencies = [read])
def get_item(job_id: UUID, service: CrawlJobServiceDep): 
    return service.get(job_id)


@router.post("", response_model = CrawlJobPublic, status_code = 201, dependencies = [write])
def create_item(data: CreateCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.create(data)


@router.post("/competitors/{competitor_id}", response_model=CrawlJobPublic, status_code=201, dependencies=[write])
async def crawl_competitor(competitor_id: UUID, service: CrawlJobServiceDep):
    return await service.crawl_competitor(competitor_id)


@router.post("/{job_id}/start", response_model = CrawlJobPublic, dependencies = [write])
def start(job_id: UUID, service: CrawlJobServiceDep): 
    return service.start(job_id)


@router.post("/{job_id}/complete", response_model = CrawlJobPublic, dependencies = [write])
def complete(job_id: UUID, data: CompleteCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.complete(job_id, records_collected = data.records_collected)


@router.post("/{job_id}/fail", response_model = CrawlJobPublic, dependencies = [write])
def fail(job_id: UUID, data: FailCrawlJobSchema, service: CrawlJobServiceDep): 
    return service.fail(job_id, error_message = data.error_message)
