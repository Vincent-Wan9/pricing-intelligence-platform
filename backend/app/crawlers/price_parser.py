from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.crawlers.base import CrawlerInvalidPriceError


def parse_price_text(value: str) -> Decimal:
    """Normalize common US/EU currency formatting into a positive decimal."""
    cleaned = re.sub(r"[^0-9,.-]", "", value.replace("\u00a0", "").strip())
    if not cleaned or cleaned in {"-", ".", ","}:
        raise CrawlerInvalidPriceError("Price element did not contain a numeric value")

    comma = cleaned.rfind(",")
    dot = cleaned.rfind(".")
    if comma >= 0 and dot >= 0:
        decimal_separator = "," if comma > dot else "."
        thousands_separator = "." if decimal_separator == "," else ","
        cleaned = cleaned.replace(thousands_separator, "").replace(decimal_separator, ".")
    elif comma >= 0:
        parts = cleaned.split(",")
        cleaned = "".join(parts) if len(parts[-1]) == 3 and len(parts) > 1 else "".join(parts[:-1]) + "." + parts[-1]
    elif cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts) if len(parts[-1]) == 3 else "".join(parts[:-1]) + "." + parts[-1]
    elif dot >= 0 and len(cleaned.split(".")[-1]) == 3:
        cleaned = cleaned.replace(".", "")

    try:
        price = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise CrawlerInvalidPriceError("Price element contained a malformed value") from exc
    if not price.is_finite() or price <= 0:
        raise CrawlerInvalidPriceError("Extracted price must be greater than zero")
    if price > Decimal("99999999.99") or price.as_tuple().exponent < -2:
        raise CrawlerInvalidPriceError("Extracted price exceeds supported precision")
    return price
