import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.crawlers.adapters.playwright import PlaywrightCompetitorCrawler
from app.crawlers.base import CrawlerHttpError, CrawlerInvalidPriceError, CrawlerSelectorNotFoundError


def mapping(selector=".price"):
    return SimpleNamespace(
        competitor_product_id=uuid4(), product_id=uuid4(), competitor_id=uuid4(),
        competitor_product_url="https://shop.example/item", price_selector=selector,
        created_at=datetime.now(timezone.utc),
    )


def browser_factory(*, prices=None, goto_effects=None, locator_effect=None):
    prices = iter(prices or ["$19.95"])
    goto_values = goto_effects or [SimpleNamespace(status=200)]
    goto_effects = iter(goto_values)
    last_goto = goto_values[-1]
    pages = []

    def new_page():
        locator = MagicMock()
        locator.first = locator
        locator.wait_for = AsyncMock(side_effect=locator_effect)
        locator.get_attribute = AsyncMock(side_effect=lambda _: None)
        locator.text_content = AsyncMock(side_effect=lambda: next(prices))
        page = MagicMock()
        page.goto = AsyncMock(side_effect=lambda *args, **kwargs: next(goto_effects, last_goto))
        page.locator = MagicMock(return_value=locator)
        page.close = AsyncMock()
        pages.append(page)
        return page

    context = MagicMock()
    context.new_page = AsyncMock(side_effect=new_page)
    context.close = AsyncMock()
    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=browser)
    playwright.stop = AsyncMock()
    starter = MagicMock()
    starter.start = AsyncMock(return_value=playwright)
    factory = MagicMock(return_value=starter)
    return factory, context, browser, playwright, pages


def test_successful_dynamic_price_extraction_uses_mapping_selector():
    factory, context, _, _, pages = browser_factory(prices=["€ 1.299,95"])
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=0)
    item = mapping("[data-testid=price]")
    result = asyncio.run(crawler.crawl_product(item))
    asyncio.run(crawler.close())
    assert result.price == Decimal("1299.95")
    pages[0].locator.assert_called_once_with("[data-testid=price]")
    pages[0].locator.return_value.wait_for.assert_awaited_once()
    context.close.assert_awaited_once()


def test_missing_selector_is_classified_and_page_is_closed():
    timeout = TimeoutError("Locator.wait_for: Timeout waiting for selector")
    factory, _, _, _, pages = browser_factory(locator_effect=timeout)
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=2, backoff_seconds=0)
    with pytest.raises(CrawlerSelectorNotFoundError):
        asyncio.run(crawler.crawl_product(mapping()))
    asyncio.run(crawler.close())
    assert len(pages) == 1
    pages[0].close.assert_awaited_once()


def test_malformed_price_is_classified_and_page_is_closed():
    factory, _, _, _, pages = browser_factory(prices=["Call for price"])
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=2)
    with pytest.raises(CrawlerInvalidPriceError):
        asyncio.run(crawler.crawl_product(mapping()))
    asyncio.run(crawler.close())
    assert len(pages) == 1
    pages[0].close.assert_awaited_once()


def test_navigation_timeout_retries_then_succeeds_and_closes_every_page():
    factory, _, _, _, pages = browser_factory(
        prices=["$25.00"],
        goto_effects=[TimeoutError("page.goto: Timeout exceeded"), SimpleNamespace(status=200)],
    )
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=1, backoff_seconds=0)
    assert asyncio.run(crawler.crawl_product(mapping())).price == Decimal("25.00")
    asyncio.run(crawler.close())
    assert len(pages) == 2
    assert all(page.close.await_count == 1 for page in pages)


def test_permanent_http_failure_is_not_retried():
    factory, _, _, _, pages = browser_factory(goto_effects=[SimpleNamespace(status=404)])
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=2, backoff_seconds=0)
    with pytest.raises(CrawlerHttpError, match="404"):
        asyncio.run(crawler.crawl_product(mapping()))
    asyncio.run(crawler.close())
    assert len(pages) == 1


def test_browser_context_is_reused_across_products():
    factory, _, browser, playwright, pages = browser_factory(prices=["$10", "$11"])
    crawler = PlaywrightCompetitorCrawler(playwright_factory=factory, max_retries=0)

    async def crawl_both():
        await crawler.start()
        await crawler.crawl_product(mapping())
        await crawler.crawl_product(mapping())
        await crawler.close()

    asyncio.run(crawl_both())
    assert browser.new_context.await_count == 1
    assert len(pages) == 2
    playwright.stop.assert_awaited_once()
