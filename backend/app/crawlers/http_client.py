from __future__ import annotations

import asyncio

import httpx

from app.crawlers.base import CrawlerFetchError, CrawlerNotFoundError
from app.core.config import settings


class CrawlerHttpClient:
    def __init__(
        self, *, timeout: float | None = None, max_retries: int | None = None,
        backoff_seconds: float | None = None, user_agent: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout = timeout if timeout is not None else settings.crawler_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.crawler_max_retries
        self.backoff_seconds = backoff_seconds if backoff_seconds is not None else settings.crawler_retry_backoff_seconds
        self.user_agent = user_agent or settings.crawler_user_agent
        self._client = client

    async def get_text(self, url: str) -> str:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                if self._client is None:
                    async with httpx.AsyncClient(
                        timeout=self.timeout, headers={"User-Agent": self.user_agent},
                        follow_redirects=True,
                    ) as client:
                        response = await client.get(url)
                else:
                    response = await self._client.get(
                        url, timeout=self.timeout, headers={"User-Agent": self.user_agent},
                        follow_redirects=True,
                    )
                if response.status_code == 404:
                    raise CrawlerNotFoundError("Competitor product page was not found (404)")
                response.raise_for_status()
                return response.text
            except CrawlerNotFoundError:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                transient = not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500
                if not transient or attempt == attempts - 1:
                    status = f"HTTP {exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else exc.__class__.__name__
                    raise CrawlerFetchError(f"Could not fetch competitor page: {status}") from exc
                await asyncio.sleep(self.backoff_seconds * (attempt + 1))
        raise CrawlerFetchError("Could not fetch competitor page")
