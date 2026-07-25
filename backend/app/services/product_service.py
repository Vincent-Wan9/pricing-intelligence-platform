from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.product import product_crud
from app.models.category import Category
from app.models.pricing_rule import PricingRule
from app.models.product import Product
from app.schemas.product_schema import (
    CreateProductSchema,
    ProductPublic,
    UpdateProductSchema,
)
from app.services import (
    ProductAuthorizationError,
    ProductConflictError,
    ProductNotFoundError,
    ProductServiceError,
    ProductValidationError,
)
from app.services.product_cache_service import ProductCacheService
from app.services.product_price_service import validate_prices
from app.utils.generate_slug import generate_slug

__all__ = [
    "ProductAuthorizationError",
    "ProductConflictError",
    "ProductNotFoundError",
    "ProductService",
    "ProductServiceError",
    "ProductValidationError",
]

NON_NULLABLE_UPDATE_FIELDS = frozenset(
    {
        "sku",
        "product_name",
        "category_id",
        "rule_id",
        "safety_stock",
        "base_price",
        "current_price",
        "auto_pricing_enabled",
        "is_active",
    }
)


class ProductService:
    """Product CRUD and lifecycle business logic."""

    def __init__(self, db: Session, cache_service: ProductCacheService) -> None:
        self.db = db
        self.cache = cache_service
        self.crud = product_crud

    async def get(self, product_id: UUID) -> ProductPublic:
        cached = await self.cache.get_by_id(product_id)
        if cached is not None:
            return cached

        result = self._to_public(self._get_model(product_id))
        await self.cache.store(result)
        return result

    async def get_by_sku(self, sku: str) -> ProductPublic:
        normalized_sku = self._normalize_sku(sku)
        cached = await self.cache.get_by_sku(normalized_sku)
        if cached is not None:
            return cached

        product = self.crud.get_by_sku(self.db, normalized_sku)
        if product is None:
            raise ProductNotFoundError(
                f"Product with SKU '{normalized_sku}' was not found"
            )

        result = self._to_public(product)
        await self.cache.store(result)
        return result

    def list(self, *, skip: int = 0, limit: int = 100, active_only: bool = False) -> list[ProductPublic]:
        self._validate_pagination(skip=skip, limit=limit)
        if active_only:
            products = self.crud.get_active_products(
                self.db,
                skip=skip,
                limit=limit,
            )
        else:
            products = self.crud.get_all(
                self.db,
                skip=skip,
                limit=limit,
            )
        return [self._to_public(product) for product in products]

    async def create(self, product_in: CreateProductSchema) -> ProductPublic:
        normalized_sku = self._normalize_sku(product_in.sku)
        if self.crud.get_by_sku(self.db, normalized_sku) is not None:
            raise ProductConflictError(
                f"Product with SKU '{normalized_sku}' already exists"
            )

        self._validate_references(
            category_id=product_in.category_id,
            rule_id=product_in.rule_id,
        )
        validate_prices(
            base_price=product_in.base_price,
            current_price=product_in.current_price,
            min_price=product_in.min_price,
            max_price=product_in.max_price,
        )

        product_data = product_in.model_dump()
        product_data["sku"] = normalized_sku
        if product_in.image_url is not None:
            product_data["image_url"] = str(product_in.image_url)

        product = Product(
            **product_data,
            slug=generate_slug(
                self.db,
                product_in.product_name,
                "product",
            ),
        )
        try:
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
        except IntegrityError as exc:
            self.db.rollback()
            raise ProductConflictError(
                "Product could not be created because its SKU, slug, "
                "or related data conflicts with an existing record"
            ) from exc

        result = self._to_public(product)
        await self.cache.store(result)
        return result

    async def update(self, product_id: UUID, product_in: UpdateProductSchema) -> ProductPublic:
        product = self._get_model(product_id)
        if not product.is_active:
            raise ProductValidationError(
                "Inactive products cannot be updated"
            )

        update_data = product_in.model_dump(exclude_unset=True)
        if not update_data:
            result = self._to_public(product)
            await self.cache.store(result)
            return result

        self._validate_update_data(update_data)
        if "current_price" in update_data:
            raise ProductValidationError(
                "Use ProductPriceService.update_price to change current_price"
            )
        if "is_active" in update_data:
            raise ProductValidationError(
                "Use deactivate or reactivate to change is_active"
            )

        old_sku = product.sku
        if "sku" in update_data:
            normalized_sku = self._normalize_sku(update_data["sku"])
            update_data["sku"] = normalized_sku
            existing = self.crud.get_by_sku(self.db, normalized_sku)
            if (
                existing is not None
                and existing.product_id != product_id
            ):
                raise ProductConflictError(
                    f"Product with SKU '{normalized_sku}' already exists"
                )

        self._validate_references(
            category_id=update_data.get(
                "category_id",
                product.category_id,
            ),
            rule_id=update_data.get("rule_id", product.rule_id),
        )
        validate_prices(
            base_price=update_data.get(
                "base_price",
                product.base_price,
            ),
            current_price=product.current_price,
            min_price=update_data.get("min_price", product.min_price),
            max_price=update_data.get("max_price", product.max_price),
        )

        if (
            "product_name" in update_data
            and update_data["product_name"] != product.product_name
        ):
            update_data["slug"] = generate_slug(
                self.db,
                update_data["product_name"],
                "product",
            )
        if update_data.get("image_url") is not None:
            update_data["image_url"] = str(update_data["image_url"])

        try:
            for field_name, value in update_data.items():
                setattr(product, field_name, value)
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
        except IntegrityError as exc:
            self.db.rollback()
            raise ProductConflictError(
                "Product could not be updated because its SKU, slug, "
                "or related data conflicts with an existing record"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

        await self.cache.invalidate(
            product.product_id,
            old_sku,
            product.sku,
        )
        result = self._to_public(product)
        await self.cache.store(result)
        return result

    async def deactivate(self, product_id: UUID) -> ProductPublic:
        return await self._set_active(product_id, is_active=False)

    async def reactivate(self, product_id: UUID) -> ProductPublic:
        product = self._get_model(product_id)
        if product.is_active:
            result = self._to_public(product)
            await self.cache.store(result)
            return result

        self._validate_references(
            category_id=product.category_id,
            rule_id=product.rule_id,
        )
        validate_prices(
            base_price=product.base_price,
            current_price=product.current_price,
            min_price=product.min_price,
            max_price=product.max_price,
        )
        return await self._set_active(
            product_id,
            is_active=True,
            product=product,
        )

    async def delete(self, product_id: UUID) -> None:
        product = self._get_model(product_id)
        sku = product.sku
        if product.is_active:
            raise ProductValidationError(
                "Active products cannot be permanently deleted; "
                "deactivate the product first"
            )

        try:
            self.crud.delete(self.db, product)
        except IntegrityError as exc:
            raise ProductConflictError(
                "Product cannot be deleted while other records reference it"
            ) from exc

        await self.cache.invalidate(product_id, sku)

    async def _set_active(self, product_id: UUID, *, is_active: bool, product: Product | None = None) -> ProductPublic:
        product = product or self._get_model(product_id)
        if product.is_active == is_active:
            result = self._to_public(product)
            await self.cache.store(result)
            return result

        try:
            product.is_active = is_active
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
        except IntegrityError as exc:
            self.db.rollback()
            action = "reactivated" if is_active else "deactivated"
            raise ProductConflictError(
                f"Product could not be {action}"
            ) from exc

        await self.cache.invalidate(product.product_id, product.sku)
        result = self._to_public(product)
        await self.cache.store(result)
        return result

    def _get_model(self, product_id: UUID) -> Product:
        product = self.crud.get(self.db, product_id)
        if product is None:
            raise ProductNotFoundError(
                f"Product {product_id} was not found"
            )
        return product

    def _validate_references(self, *, category_id: UUID, rule_id: UUID) -> None:
        if self.db.get(Category, category_id) is None:
            raise ProductValidationError(
                f"Category {category_id} does not exist"
            )

        pricing_rule = self.db.get(PricingRule, rule_id)
        if pricing_rule is None:
            raise ProductValidationError(
                f"Pricing rule {rule_id} does not exist"
            )
        if not pricing_rule.is_active:
            raise ProductValidationError(
                "Inactive pricing rules cannot be assigned to products"
            )

    @staticmethod
    def _validate_update_data(update_data: dict[str, object]) -> None:
        null_fields = sorted(
            field
            for field in NON_NULLABLE_UPDATE_FIELDS
            if field in update_data and update_data[field] is None
        )
        if null_fields:
            raise ProductValidationError(
                "These fields cannot be null: "
                + ", ".join(null_fields)
            )

    @staticmethod
    def _validate_pagination(*, skip: int, limit: int) -> None:
        if skip < 0:
            raise ProductValidationError("skip cannot be negative")
        if not 1 <= limit <= 1000:
            raise ProductValidationError(
                "limit must be between 1 and 1000"
            )

    @staticmethod
    def _normalize_sku(sku: str) -> str:
        normalized_sku = sku.strip().upper()
        if not normalized_sku:
            raise ProductValidationError("SKU cannot be empty")
        return normalized_sku

    @staticmethod
    def _to_public(product: Product) -> ProductPublic:
        return ProductPublic.model_validate(product)
