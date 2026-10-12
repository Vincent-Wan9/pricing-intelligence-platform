from typing import Literal
from uuid import uuid4

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product

SlugContext = Literal["product", "category"]


def generate_slug(db: Session, name: str, context: SlugContext) -> str:
    """Return an available slug within the model's column length.

    Availability is checked in the current session; concurrent writes still
    require a database uniqueness constraint and conflict handling by callers.
    """
    if context == "product":
        model = Product
    elif context == "category":
        model = Category
    else:
        raise ValueError(f"Invalid slug context: {context}")

    max_length = model.__table__.c.slug.type.length
    base_slug = (slugify(name, lowercase=True) or context)[:max_length].rstrip("-")

    candidate = base_slug
    counter = 0
    while db.scalar(select(model.slug).where(model.slug == candidate)) is not None:
        counter += 1
        suffix = f"-{counter}"
        if len(suffix) >= max_length:
            raise ValueError(f"No available slug for context: {context}")
        candidate = f"{base_slug[:max_length - len(suffix)].rstrip('-')}{suffix}"

    return candidate


def generate_sku(name: str, prefix: str = "PRD") -> str:
    """Return a SKU candidate; callers must handle database uniqueness conflicts."""
    base = slugify(name, separator="", lowercase=False)[:5].upper() or "PRD"
    unique_part = uuid4().hex[:4].upper()
    return f"{prefix}-{base}-{unique_part}"
