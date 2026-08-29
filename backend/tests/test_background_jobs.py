import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.competitor import Competitor
from app.models.crawl_job import CrawlJob
from app.schemas.crawl_job_schema import CrawlJobPublic
from app.services.crawl_job_service import (
    CrawlJobEnqueueError,
    CrawlJobService,
)
from app.tasks.celery_app import celery_app
from app.tasks import crawl_tasks
from app.tasks import forecast_tasks


def public_job(competitor_id, job_id=None, status="pending"):
    return CrawlJobPublic(
        job_id=job_id or uuid4(),
        competitor_id=competitor_id,
        status=status,
        started_at=datetime.now(timezone.utc) if status != "pending" else None,
        completed_at=datetime.now(timezone.utc) if status in {"completed", "failed"} else None,
        records_collected=1 if status == "completed" else 0,
        error_message="failure" if status == "failed" else None,
    )


def add_competitor(db_session):
    competitor = Competitor(
        competitor_name=f"Store {uuid4()}",
        website_url=f"https://{uuid4()}.example.com",
        is_active=True,
    )
    db_session.add(competitor)
    db_session.commit()
    db_session.refresh(competitor)
    return competitor


def test_enqueue_creates_pending_job_and_dispatches_id(db_session):
    competitor = add_competitor(db_session)
    dispatched = []

    job, created = CrawlJobService(db_session).enqueue_competitor(
        competitor.competitor_id, dispatcher=dispatched.append
    )

    assert created is True
    assert job.status == "pending"
    assert job.started_at is None
    assert dispatched == [str(job.job_id)]


def test_duplicate_active_job_is_returned_without_second_dispatch(db_session):
    competitor = add_competitor(db_session)
    dispatched = []
    service = CrawlJobService(db_session)

    first, first_created = service.enqueue_competitor(
        competitor.competitor_id, dispatcher=dispatched.append
    )
    second, second_created = service.enqueue_competitor(
        competitor.competitor_id, dispatcher=dispatched.append
    )

    assert first_created is True
    assert second_created is False
    assert second.job_id == first.job_id
    assert dispatched == [str(first.job_id)]
    assert "uq_crawl_jobs_active_competitor" in {index.name for index in CrawlJob.__table__.indexes}


def test_enqueue_failure_marks_job_failed_and_rolls_back_to_terminal_state(db_session):
    competitor = add_competitor(db_session)

    def unavailable(_job_id):
        raise ConnectionError("broker unavailable")

    with pytest.raises(CrawlJobEnqueueError):
        CrawlJobService(db_session).enqueue_competitor(
            competitor.competitor_id, dispatcher=unavailable
        )

    job = db_session.query(CrawlJob).one()
    assert job.status == "failed"
    assert job.completed_at is not None
    assert "enqueued" in job.error_message


def test_execute_job_persists_unexpected_worker_failure():
    competitor_id, job_id = uuid4(), uuid4()
    db = MagicMock()
    service = CrawlJobService(db)
    service._get_model = MagicMock(return_value=SimpleNamespace(
        job_id=job_id, competitor_id=competitor_id, status="running"
    ))
    service.claim = MagicMock(return_value=public_job(competitor_id, job_id, "running"))
    service._crawl_claimed_job = AsyncMock(side_effect=RuntimeError("database disconnected"))
    failed = public_job(competitor_id, job_id, "failed")
    service._fail_safely = MagicMock(return_value=failed)

    result = asyncio.run(service.execute_job(job_id))

    assert result.status == "failed"
    db.rollback.assert_called_once()
    service._fail_safely.assert_called_once()


def test_crawl_job_save_rolls_back_unexpected_transaction_failure():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("connection lost")

    with pytest.raises(RuntimeError, match="connection lost"):
        CrawlJobService(db)._save(MagicMock())

    db.rollback.assert_called_once()


def test_worker_owns_and_closes_database_session(monkeypatch):
    job_id, competitor_id = uuid4(), uuid4()
    db = MagicMock()
    redis = MagicMock()
    redis.connect = AsyncMock()
    redis.close = AsyncMock()
    result = public_job(competitor_id, job_id, "completed")
    execute = AsyncMock(return_value=result)

    monkeypatch.setattr(crawl_tasks, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(crawl_tasks, "RedisClient", MagicMock(return_value=redis))
    monkeypatch.setattr(crawl_tasks, "CrawlJobService", MagicMock(
        return_value=SimpleNamespace(execute_job=execute)
    ))

    payload = asyncio.run(crawl_tasks._execute(job_id))

    assert payload["status"] == "completed"
    execute.assert_awaited_once_with(job_id)
    db.close.assert_called_once()
    redis.close.assert_awaited_once()


def test_beat_schedule_dispatches_scheduler_task_every_six_hours():
    entry = celery_app.conf.beat_schedule["enqueue-scheduled-competitor-crawls"]
    assert entry["task"] == "app.tasks.enqueue_scheduled_competitor_crawls"
    assert entry["schedule"] == 6 * 60 * 60
    assert crawl_tasks.execute_competitor_crawl.name == "app.tasks.execute_competitor_crawl"


def test_scheduler_enqueues_jobs_without_executing_crawler(monkeypatch):
    competitor_ids = [uuid4(), uuid4()]
    db = MagicMock()
    db.scalars.return_value.all.return_value = competitor_ids
    enqueue = MagicMock(side_effect=[(public_job(competitor_ids[0]), True),
                                    (public_job(competitor_ids[1]), False)])
    monkeypatch.setattr(crawl_tasks, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(crawl_tasks, "CrawlJobService", MagicMock(
        return_value=SimpleNamespace(enqueue_competitor=enqueue)
    ))

    result = crawl_tasks.enqueue_scheduled_competitor_crawls.run()

    assert result == {"competitors": 2, "enqueued": 1, "failures": 0}
    assert enqueue.call_count == 2
    db.close.assert_called_once()


def test_forecast_beat_schedule_and_per_product_failure_isolation(monkeypatch):
    entry = celery_app.conf.beat_schedule["refresh-demand-forecasts"]
    assert entry["task"] == "app.tasks.refresh_demand_forecasts"

    product_ids = [uuid4(), uuid4()]
    db = MagicMock()
    db.scalars.return_value.all.return_value = product_ids
    generate = MagicMock(side_effect=[SimpleNamespace(), RuntimeError("training failed")])
    monkeypatch.setattr(forecast_tasks, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(forecast_tasks, "DemandForecastService", MagicMock(
        return_value=SimpleNamespace(generate=generate)
    ))

    result = forecast_tasks.refresh_demand_forecasts.run()

    assert result == {"products": 2, "generated": 1, "failures": 1}
    assert generate.call_count == 2
    db.rollback.assert_called_once()
    db.close.assert_called_once()
