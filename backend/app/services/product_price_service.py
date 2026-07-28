import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.product import product_crud
from app.models.product import Product
from app.models.product_price_history import ProductPriceHistory
from app.models.user import User
from app.schemas.product_schema import ProductPublic
from app.services import (
    ProductAuthorizationError,
    ProductConflictError,
    ProductNotFoundError,
    ProductValidationError,
)
from app.services.pricing_validation import validate_prices
from app.services.product_cache_service import ProductCacheService

logger = logging.getLogger(__name__)


class ProductPriceService:
    """Authorized product price changes and price-history recording."""

    ALLOWED_UPDATE_ROLES = {"admin", "approver"}

    def __init__(self, db: Session, cache_service: ProductCacheService) -> None:
        self.db = db
        self.cache = cache_service
        self.crud = product_crud

    async def update_price(self, product_id: UUID, new_price: Decimal, *, user: User, reason: str) -> ProductPublic:
        self._validate_permission(user)

        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ProductValidationError(
                "A reason is required when changing a product price"
            )

        product = self._get_model(product_id)
        if not product.is_active:
            raise ProductValidationError(
                "Inactive products cannot receive price updates"
            )
        if new_price == product.current_price:
            raise ProductValidationError(
                "The new price must be different from the current price"
            )

        validate_prices(
            base_price=product.base_price,
            current_price=new_price,
            min_price=product.min_price,
            max_price=product.max_price,
        )
        old_price = product.current_price

        try:
            product.current_price = new_price
            self.db.add(product)
            self.db.flush()
            self.db.add(
                ProductPriceHistory(
                    product_id=product.product_id,
                    old_price=old_price,
                    new_price=new_price,
                )
            )
            self.db.commit()
            self.db.refresh(product)
        except IntegrityError as exc:
            self.db.rollback()
            raise ProductConflictError(
                "The product price could not be updated"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

        logger.info(
            "Product %s price changed from %s to %s by user %s: %s",
            product.product_id,
            old_price,
            new_price,
            user.user_id,
            normalized_reason,
        )
        await self.cache.invalidate(product.product_id, product.sku)
        result = ProductPublic.model_validate(product)
        await self.cache.store(result)
        return result

    def _get_model(self, product_id: UUID) -> Product:
        product = self.crud.get(self.db, product_id)
        if product is None:
            raise ProductNotFoundError(
                f"Product {product_id} was not found"
            )
        return product

    @classmethod
    def _validate_permission(cls, user: User) -> None:
        if not user.is_active:
            raise ProductAuthorizationError(
                "Inactive users cannot change product prices"
            )

        role = getattr(user.role, "value", user.role)
        if role not in cls.ALLOWED_UPDATE_ROLES:
            raise ProductAuthorizationError(
                "Only admins and approvers can directly change product prices"
            )
