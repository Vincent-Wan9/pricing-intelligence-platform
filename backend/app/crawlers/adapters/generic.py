from app.crawlers.base import BaseCompetitorCrawler, CrawledProduct
from app.crawlers.http_client import CrawlerHttpClient
from app.crawlers.parsers import SimpleHtmlProductParser
from app.models.competitor_product import CompetitorProduct


class GenericHttpCrawler(BaseCompetitorCrawler):
    def __init__(self, client: CrawlerHttpClient | None = None, parser: SimpleHtmlProductParser | None = None) -> None:
        self.client = client or CrawlerHttpClient()
        self.parser = parser or SimpleHtmlProductParser()

    async def fetch_product(self, mapping: CompetitorProduct) -> str:
        return await self.client.get_text(mapping.competitor_product_url)

    def parse_product(self, html: str, mapping: CompetitorProduct) -> CrawledProduct:
        return self.parser.parse(html)
