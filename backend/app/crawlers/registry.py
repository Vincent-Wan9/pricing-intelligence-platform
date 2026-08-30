from __future__ import annotations

from uuid import UUID

from app.crawlers.adapters import PlaywrightCompetitorCrawler
from app.crawlers.base import BaseCompetitorCrawler


class CrawlerRegistry:
    """Maps competitors to adapters without coupling orchestration to retailer HTML."""

    def __init__(self, default: BaseCompetitorCrawler | None = None) -> None:
        self.default = default or PlaywrightCompetitorCrawler()
        self._adapters: dict[UUID, BaseCompetitorCrawler] = {}

    def register(self, competitor_id: UUID, crawler: BaseCompetitorCrawler) -> None:
        self._adapters[competitor_id] = crawler

    def get(self, competitor_id: UUID) -> BaseCompetitorCrawler:
        return self._adapters.get(competitor_id, self.default)
