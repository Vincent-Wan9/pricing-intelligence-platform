from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.schemas.competitor_schema import CreateCompetitorSchema
from app.services.competitor_service import (
    CompetitorConflictError,
    CompetitorService,
)
from app.services.crawl_job_service import CrawlJobConflictError, CrawlJobService


def test_competitor_create_rolls_back_unique_constraint_conflict() -> None:
    db = MagicMock()
    service = CompetitorService(db)
    db.scalar.return_value = None
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))

    with pytest.raises(CompetitorConflictError):
        service.create(
            CreateCompetitorSchema(
                competitor_name="Example Store",
                website_url="https://example.com",
            )
        )

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


def test_crawl_job_update_rolls_back_and_translates_conflict() -> None:
    db = MagicMock()
    db.commit.side_effect = IntegrityError("update", {}, Exception("conflict"))
    job = MagicMock()

    with pytest.raises(CrawlJobConflictError, match="updated"):
        CrawlJobService(db)._save(job)

    db.add.assert_called_once_with(job)
    db.rollback.assert_called_once()
    db.refresh.assert_not_called()
