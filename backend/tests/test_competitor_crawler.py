import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import IntegrityError

from app.crawlers.base import (
    BaseCompetitorCrawler,
    CrawledProduct,
    CrawlerFetchError,
    CrawlerNotFoundError,
    CrawlerParseError,
)
from app.crawlers.http_client import CrawlerHttpClient
from app.crawlers.price_parser import parse_price_text
from app.crawlers.parsers import SimpleHtmlProductParser
from app.crawlers.registry import CrawlerRegistry
from app.models.competitor_price import CompetitorPrice
from app.schemas.competitor_price_schema import CreateCompetitorPriceSchema
from app.schemas.competitor_product_schema import CreateCompetitorProductSchema
from app.services.competitor_price_service import CompetitorPriceConflictError, CompetitorPriceService
from app.services.competitor_product_service import CompetitorProductConflictError, CompetitorProductService
from app.services.crawl_job_service import CrawlJobService


def mapping(*, active=True):
    return SimpleNamespace(
        competitor_product_id=uuid4(), product_id=uuid4(), competitor_id=uuid4(),
        competitor_sku="EXT-1", competitor_product_name="External product",
        competitor_product_url="https://shop.example/products/1", is_active=active,
        price_selector=".product-price",
        created_at=datetime.now(timezone.utc),
    )


class FakeCrawler(BaseCompetitorCrawler):
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)

    async def fetch_product(self, mapping):
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def parse_product(self, html, mapping):
        return SimpleHtmlProductParser().parse(html)


def html(price="19.95", *, currency="USD"):
    return f'<meta property="product:price:amount" content="{price}"><meta property="product:price:currency" content="{currency}"><div data-in-stock="true" data-stock-qty="4"></div>'


def test_simple_parser_extracts_decimal_and_availability():
    result = SimpleHtmlProductParser().parse(html())
    assert result.price == Decimal("19.95")
    assert result.in_stock is True
    assert result.stock_qty == 4


@pytest.mark.parametrize("page", ["<html></html>", '<div data-price="not-a-price"></div>'])
def test_simple_parser_rejects_missing_or_invalid_price(page):
    with pytest.raises(CrawlerParseError):
        SimpleHtmlProductParser().parse(page)


def test_crawled_product_rejects_currency_and_non_positive_price():
    with pytest.raises(CrawlerParseError, match="currency"):
        CrawledProduct(Decimal("10"), currency="EUR").validate()
    with pytest.raises(CrawlerParseError, match="greater than zero"):
        CrawledProduct(Decimal("0")).validate()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("$1,299.95", Decimal("1299.95")), ("€ 1.299,95", Decimal("1299.95")), ("19,95", Decimal("19.95"))],
)
def test_price_text_normalizes_currency_and_decimal_formats(raw, expected):
    assert parse_price_text(raw) == expected


@pytest.mark.parametrize("raw", ["not available", "$0.00", "-"])
def test_price_text_rejects_malformed_or_zero_values(raw):
    with pytest.raises(CrawlerParseError):
        parse_price_text(raw)


def test_http_client_success_and_user_agent():
    async def handler(request):
        assert request.headers["user-agent"] == "crawler-test"
        return httpx.Response(200, text=html())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    crawler = CrawlerHttpClient(client=client, user_agent="crawler-test", max_retries=0)
    assert asyncio.run(crawler.get_text("https://shop.example/item")) == html()
    asyncio.run(client.aclose())


def test_http_404_is_not_retried():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(404, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(CrawlerNotFoundError):
        asyncio.run(CrawlerHttpClient(client=client, max_retries=2).get_text("https://shop.example/missing"))
    assert calls == 1
    asyncio.run(client.aclose())


def test_http_500_retries_then_succeeds():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(500 if calls < 3 else 200, request=request, text=html())

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = asyncio.run(CrawlerHttpClient(client=client, max_retries=2, backoff_seconds=0).get_text("https://shop.example/item"))
    assert result == html()
    assert calls == 3
    asyncio.run(client.aclose())


def test_http_timeout_becomes_fetch_error():
    async def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(CrawlerFetchError, match="ReadTimeout"):
        asyncio.run(CrawlerHttpClient(client=client, max_retries=0).get_text("https://shop.example/slow"))
    asyncio.run(client.aclose())


def test_mapping_create_and_duplicate_rejected():
    db = MagicMock()
    db.get.return_value = SimpleNamespace(is_active=True)
    db.scalar.return_value = None
    def populate_defaults(instance):
        instance.competitor_product_id = uuid4()
        instance.created_at = datetime.now(timezone.utc)
    db.refresh.side_effect = populate_defaults
    service = CompetitorProductService(db)
    payload = CreateCompetitorProductSchema(
        product_id=uuid4(), competitor_id=uuid4(), competitor_sku="EXT-1",
        competitor_product_name="External", competitor_product_url="https://shop.example/1",
    )
    result = service.create(payload)
    assert result.is_active is True
    db.scalar.return_value = SimpleNamespace(competitor_product_id=uuid4())
    with pytest.raises(CompetitorProductConflictError, match="already mapped"):
        service.create(payload)


def _job_result(competitor_id, job_id, status, count=0, error=None):
    return SimpleNamespace(
        job_id=job_id, competitor_id=competitor_id, status=status,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) if status in {"completed", "failed"} else None,
        records_collected=count, error_message=error,
    )


def orchestrator(outcomes, mappings):
    competitor_id = mappings[0].competitor_id if mappings else uuid4()
    db = MagicMock()
    db.get.return_value = SimpleNamespace(competitor_product=mappings)
    registry = CrawlerRegistry(default=FakeCrawler(outcomes))
    cache = SimpleNamespace(invalidate_price_inputs=AsyncMock())
    service = CrawlJobService(db, registry=registry, cache_service=cache, request_delay_seconds=0)
    job_id = uuid4()
    service.create = MagicMock(return_value=_job_result(competitor_id, job_id, "pending"))
    service.start = MagicMock(return_value=_job_result(competitor_id, job_id, "running"))
    service.complete = MagicMock(side_effect=lambda _, records_collected, error_message=None: _job_result(competitor_id, job_id, "completed", records_collected, error_message))
    service.fail = MagicMock(side_effect=lambda _, error_message: _job_result(competitor_id, job_id, "failed", error=error_message))
    return service, cache, competitor_id


def test_partial_failure_completes_and_preserves_success(monkeypatch):
    first, second = mapping(), mapping()
    second.competitor_id = first.competitor_id
    service, cache, competitor_id = orchestrator([html(), CrawlerFetchError("timeout")], [first, second])
    record = AsyncMock()
    monkeypatch.setattr("app.services.crawl_job_service.CompetitorPriceService.record", record)
    result = asyncio.run(service.crawl_competitor(competitor_id))
    assert result.status == "completed"
    assert result.records_collected == 1
    assert "Partial failures" in result.error_message
    record.assert_awaited_once()
    cache.invalidate_price_inputs.assert_awaited_once()


def test_inactive_mapping_is_skipped(monkeypatch):
    inactive = mapping(active=False)
    service, _, competitor_id = orchestrator([html()], [inactive])
    record = AsyncMock()
    monkeypatch.setattr("app.services.crawl_job_service.CompetitorPriceService.record", record)
    result = asyncio.run(service.crawl_competitor(competitor_id))
    assert result.status == "failed"
    assert "No active" in result.error_message
    record.assert_not_called()


def test_total_failure_marks_job_failed_with_error(monkeypatch):
    item = mapping()
    service, _, competitor_id = orchestrator([CrawlerNotFoundError("not found")], [item])
    monkeypatch.setattr("app.services.crawl_job_service.CompetitorPriceService.record", AsyncMock())
    result = asyncio.run(service.crawl_competitor(competitor_id))
    assert result.status == "failed"
    assert "not found" in result.error_message


def test_price_duplicate_conflict_rolls_back_and_unique_constraint_exists():
    constraint_names = {constraint.name for constraint in CompetitorPrice.__table__.constraints}
    assert "uq_crawl_job_competitor_product" in constraint_names
    db = MagicMock()
    db.get.return_value = mapping()
    db.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    data = CreateCompetitorPriceSchema(
        competitor_product_id=uuid4(), crawl_job_id=uuid4(), competitor_price=Decimal("12.50"),
        crawl_timestamp=datetime.now(timezone.utc),
    )
    with pytest.raises(CompetitorPriceConflictError):
        asyncio.run(CompetitorPriceService(db).record(data))
    db.rollback.assert_called_once()


def test_unchanged_price_updates_mapping_without_inserting_duplicate():
    item = mapping()
    latest = SimpleNamespace(
        competitor_price=Decimal("12.50"), stock_qty=4, in_stock=True
    )
    db = MagicMock()
    db.get.return_value = item
    db.scalar.return_value = latest
    observed_at = datetime.now(timezone.utc)
    data = CreateCompetitorPriceSchema(
        competitor_product_id=item.competitor_product_id,
        crawl_job_id=uuid4(),
        competitor_price=Decimal("12.50"),
        stock_qty=4,
        in_stock=True,
        crawl_timestamp=observed_at,
    )
    result = asyncio.run(CompetitorPriceService(db).record(data, skip_unchanged=True))
    assert result is None
    assert item.last_crawled_at == observed_at
    assert item.last_crawl_error is None
    db.commit.assert_called_once()
    db.refresh.assert_not_called()
