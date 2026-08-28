from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "pricing_intelligence",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.crawl_tasks", "app.tasks.forecast_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    beat_schedule={
        "enqueue-scheduled-competitor-crawls": {
            "task": "app.tasks.enqueue_scheduled_competitor_crawls",
            "schedule": settings.competitor_crawl_schedule_seconds,
        },
        "refresh-demand-forecasts": {
            "task": "app.tasks.refresh_demand_forecasts",
            "schedule": settings.demand_forecast_schedule_seconds,
        },
    },
)
