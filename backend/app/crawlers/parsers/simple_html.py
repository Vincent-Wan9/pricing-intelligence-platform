from __future__ import annotations

from html.parser import HTMLParser

from app.crawlers.base import CrawledProduct, CrawlerParseError
from app.crawlers.price_parser import parse_price_text


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key:
                self.values[key] = values.get("content", "")
        for key in ("data-price", "data-currency", "data-in-stock", "data-stock-qty"):
            if key in values and key not in self.values:
                self.values[key] = values[key]


class SimpleHtmlProductParser:
    """Small stable MVP parser for schema.org/OpenGraph metadata or data-* fixtures."""

    PRICE_KEYS = ("product:price:amount", "og:price:amount", "data-price")
    CURRENCY_KEYS = ("product:price:currency", "og:price:currency", "data-currency")

    def parse(self, html: str) -> CrawledProduct:
        parser = _MetadataParser()
        parser.feed(html)
        raw_price = next((parser.values[key] for key in self.PRICE_KEYS if parser.values.get(key)), None)
        if raw_price is None:
            raise CrawlerParseError("Product page did not contain supported price metadata")
        price = parse_price_text(raw_price)
        currency = next((parser.values[key] for key in self.CURRENCY_KEYS if parser.values.get(key)), "USD")
        raw_stock = parser.values.get("data-in-stock")
        in_stock = None if raw_stock is None else raw_stock.strip().lower() in {"1", "true", "yes", "in_stock", "instock"}
        raw_qty = parser.values.get("data-stock-qty")
        try:
            stock_qty = int(raw_qty) if raw_qty is not None else None
        except ValueError as exc:
            raise CrawlerParseError("Product page contained an invalid stock quantity") from exc
        return CrawledProduct(price=price, currency=currency, in_stock=in_stock, stock_qty=stock_qty)
