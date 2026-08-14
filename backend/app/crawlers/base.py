from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.models.competitor_product import CompetitorProduct


class CrawlerError(Exception):
    """Safe, user-readable failure while fetching or parsing a public page."""


class CrawlerFetchError(CrawlerError):
    pass


class CrawlerNotFoundError(CrawlerFetchError):
    pass


class CrawlerParseError(CrawlerError):
    pass


@dataclass(frozen=True)
class CrawledProduct:
    price: Decimal
    currency: str = "USD"
    in_stock: bool | None = None
    stock_qty: int | None = None

    def validate(self, *, expected_currency: str = "USD") -> "CrawledProduct":
        if not self.price.is_finite() or self.price <= 0:
            raise CrawlerParseError("Parsed price must be greater than zero")
        if self.currency.upper() != expected_currency.upper():
            raise CrawlerParseError(f"Unsupported currency: {self.currency}")
        if self.stock_qty is not None and self.stock_qty < 0:
            raise CrawlerParseError("Parsed stock quantity cannot be negative")
        return self


class BaseCompetitorCrawler(ABC):
    @abstractmethod
    async def fetch_product(self, mapping: CompetitorProduct) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_product(self, html: str, mapping: CompetitorProduct) -> CrawledProduct:
        raise NotImplementedError

    async def crawl_product(self, mapping: CompetitorProduct) -> CrawledProduct:
        html = await self.fetch_product(mapping)
        if not html or not html.strip():
            raise CrawlerParseError("Competitor returned an empty product page")
        return self.parse_product(html, mapping).validate()
