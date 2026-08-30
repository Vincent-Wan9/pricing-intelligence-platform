from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.crawlers.base import (
    BaseCompetitorCrawler,
    CrawledProduct,
    CrawlerFetchError,
    CrawlerHttpError,
    CrawlerNavigationTimeoutError,
    CrawlerParseError,
    CrawlerSelectorNotFoundError,
)
from app.crawlers.price_parser import parse_price_text
from app.models.competitor_product import CompetitorProduct

logger = logging.getLogger(__name__)


class PlaywrightCompetitorCrawler(BaseCompetitorCrawler):
    """Browser adapter that reuses one browser context for a complete crawl job."""

    DEFAULT_PRICE_SELECTOR = (
        '[itemprop="price"], meta[property="product:price:amount"], '
        'meta[property="og:price:amount"], [data-price]'
    )

    def __init__(
        self,
        *,
        timeout_seconds: float | None = None,
        selector_timeout_seconds: float | None = None,
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
        user_agent: str | None = None,
        playwright_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.timeout_ms = int((timeout_seconds or settings.crawler_timeout_seconds) * 1000)
        self.selector_timeout_ms = int((selector_timeout_seconds or settings.crawler_selector_timeout_seconds) * 1000)
        self.max_retries = settings.crawler_max_retries if max_retries is None else max_retries
        self.backoff_seconds = settings.crawler_retry_backoff_seconds if backoff_seconds is None else backoff_seconds
        self.user_agent = user_agent or settings.crawler_user_agent
        self._factory = playwright_factory
        self._playwright = None
        self._browser = None
        self._context = None

    async def start(self) -> None:
        if self._context is not None:
            return
        if self._factory is None:
            from playwright.async_api import async_playwright

            self._factory = async_playwright
        self._playwright = await self._factory().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=self.user_agent,
            locale="en-US",
            viewport={"width": 1366, "height": 768},
        )
        self._context.set_default_timeout(self.selector_timeout_ms)
        self._context.set_default_navigation_timeout(self.timeout_ms)

    async def close(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        finally:
            self._context = None
            try:
                if self._browser is not None:
                    await self._browser.close()
            finally:
                self._browser = None
                if self._playwright is not None:
                    await self._playwright.stop()
                self._playwright = None

    async def fetch_product(self, mapping: CompetitorProduct) -> str:
        raise NotImplementedError("Playwright extracts rendered price elements directly")

    def parse_product(self, html: str, mapping: CompetitorProduct) -> CrawledProduct:
        raise NotImplementedError("Playwright extracts rendered price elements directly")

    async def crawl_product(self, mapping: CompetitorProduct) -> CrawledProduct:
        await self.start()
        selector = getattr(mapping, "price_selector", None) or self.DEFAULT_PRICE_SELECTOR
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            page = await self._context.new_page()
            try:
                response = await page.goto(
                    str(mapping.competitor_product_url),
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                if response is not None and response.status >= 500:
                    raise CrawlerFetchError(f"Temporary HTTP/page failure: status {response.status}")
                if response is not None and response.status >= 400:
                    raise CrawlerHttpError(f"HTTP/page failure: status {response.status}")
                locator = page.locator(selector).first
                await locator.wait_for(state="attached", timeout=self.selector_timeout_ms)
                raw_price = await locator.get_attribute("content") or await locator.text_content()
                if raw_price is None:
                    raise CrawlerSelectorNotFoundError("Price selector matched an empty element")
                result = CrawledProduct(price=parse_price_text(raw_price)).validate()
                logger.info(
                    "crawler_price_extracted competitor_id=%s mapping_id=%s product_id=%s attempt=%s",
                    mapping.competitor_id, mapping.competitor_product_id, mapping.product_id, attempt + 1,
                )
                return result
            except (CrawlerHttpError, CrawlerParseError):
                raise
            except CrawlerFetchError as exc:
                if attempt < attempts - 1:
                    logger.warning(
                        "crawler_retry competitor_id=%s mapping_id=%s failure=%s attempt=%s",
                        mapping.competitor_id, mapping.competitor_product_id, exc, attempt + 1,
                    )
                    await asyncio.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise
            except Exception as exc:
                failure = self._classify_playwright_error(exc)
                if isinstance(failure, (CrawlerNavigationTimeoutError, CrawlerFetchError)) and attempt < attempts - 1:
                    logger.warning(
                        "crawler_retry competitor_id=%s mapping_id=%s failure=%s attempt=%s",
                        mapping.competitor_id, mapping.competitor_product_id, failure, attempt + 1,
                    )
                    await asyncio.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise failure from exc
            finally:
                await page.close()
        raise CrawlerFetchError("Unexpected crawler retry exhaustion")

    @staticmethod
    def _classify_playwright_error(exc: Exception) -> Exception:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        if "timeout" in name or "timeout" in message:
            if "selector" in message or "locator" in message or "waiting for" in message:
                return CrawlerSelectorNotFoundError("Price selector was not found before timeout")
            return CrawlerNavigationTimeoutError("Navigation timed out")
        if name == "error" or "navigation" in message or "net::" in message:
            return CrawlerFetchError(f"Temporary navigation failure: {exc}")
        return CrawlerFetchError(f"Unexpected browser failure: {exc}")
