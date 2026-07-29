from uuid import UUID

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.inventory import inventory_crud
from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.inventory_schema import (
    CreateInventorySchema,
    InventoryPublic,
    UpdateInventorySchema,
)


class InventoryServiceError(Exception):
    pass


class InventoryNotFoundError(InventoryServiceError):
    pass


class InventoryConflictError(InventoryServiceError):
    pass


class InventoryValidationError(InventoryServiceError):
    pass


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crud = inventory_crud

    def get(self, inventory_id: UUID) -> InventoryPublic:
        return InventoryPublic.model_validate(self._get_model(inventory_id))

    def get_by_product(self, product_id: UUID) -> InventoryPublic:
        inventory = self.crud.get_by_product(self.db, product_id)
        if inventory is None:
            raise InventoryNotFoundError(
                f"Inventory for product {product_id} was not found"
            )
        return InventoryPublic.model_validate(inventory)

    def list(self, *, skip: int = 0, limit: int = 100) -> list[InventoryPublic]:
        self._validate_pagination(skip, limit)
        records = self.crud.get_all(self.db, skip=skip, limit=limit)
        return [InventoryPublic.model_validate(item) for item in records]

    def create(self, inventory_in: CreateInventorySchema) -> InventoryPublic:
        self._validate_product(inventory_in.product_id)

        if self.crud.get_by_product(self.db, inventory_in.product_id) is not None:
            raise InventoryConflictError(
                f"Inventory already exists for product {inventory_in.product_id}"
            )

        self._validate_levels(
            on_hand_qty=inventory_in.on_hand_qty,
        )

        inventory = Inventory(**inventory_in.model_dump())

        try:
            self.db.add(inventory)
            self.db.commit()
            self.db.refresh(inventory)
        except IntegrityError as exc:
            self.db.rollback()
            raise InventoryConflictError(
                "Inventory could not be created because its data conflicts "
                "with an existing record"
            ) from exc

        return InventoryPublic.model_validate(inventory)

    def update(
        self,
        inventory_id: UUID,
        inventory_in: UpdateInventorySchema,
    ) -> InventoryPublic:
        inventory = self._get_model(inventory_id)
        update_data = inventory_in.model_dump(exclude_unset=True)

        resulting_on_hand = update_data.get("on_hand_qty", inventory.on_hand_qty)
        self._validate_levels(on_hand_qty=resulting_on_hand)

        try:
            for field, value in update_data.items():
                setattr(inventory, field, value)
            self.db.add(inventory)
            self.db.commit()
            self.db.refresh(inventory)
        except IntegrityError as exc:
            self.db.rollback()
            raise InventoryConflictError("Inventory could not be updated") from exc

        return InventoryPublic.model_validate(inventory)

    def adjust_stock(
        self,
        product_id: UUID,
        quantity_delta: int,
    ) -> InventoryPublic:
        # Perform the read/check/write in one statement. This avoids lost
        # updates when multiple workers adjust the same product concurrently.
        stmt = (
            update(Inventory)
            .where(
                Inventory.product_id == product_id,
                Inventory.on_hand_qty + quantity_delta >= 0,
            )
            .values(on_hand_qty=Inventory.on_hand_qty + quantity_delta)
            .returning(Inventory)
        )
        try:
            inventory = self.db.execute(stmt).scalar_one_or_none()
            if inventory is None:
                existing = self.crud.get_by_product(self.db, product_id)
                if existing is None:
                    raise InventoryNotFoundError(
                        f"Inventory for product {product_id} was not found"
                    )
                raise InventoryValidationError(
                    "Stock adjustment cannot make on_hand_qty negative"
                )
            self.db.commit()
            self.db.refresh(inventory)
        except IntegrityError as exc:
            self.db.rollback()
            raise InventoryConflictError("Stock could not be adjusted") from exc
        except Exception:
            self.db.rollback()
            raise

        return InventoryPublic.model_validate(inventory)

    def delete(self, inventory_id: UUID) -> None:
        inventory = self._get_model(inventory_id)
        try:
            self.db.delete(inventory)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise InventoryConflictError(
                "Inventory cannot be deleted while other records reference it"
            ) from exc

    def _get_model(self, inventory_id: UUID) -> Inventory:
        inventory = self.crud.get(self.db, inventory_id)
        if inventory is None:
            raise InventoryNotFoundError(
                f"Inventory {inventory_id} was not found"
            )
        return inventory

    def _validate_product(self, product_id: UUID) -> None:
        if self.db.get(Product, product_id) is None:
            raise InventoryValidationError(
                f"Product {product_id} does not exist"
            )

    @staticmethod
    def _validate_levels(
        *,
        on_hand_qty: int,
    ) -> None:
        if on_hand_qty < 0:
            raise InventoryValidationError("on_hand_qty cannot be negative")

    @staticmethod
    def _validate_pagination(skip: int, limit: int) -> None:
        if skip < 0:
            raise InventoryValidationError("skip cannot be negative")
        if not 1 <= limit <= 1000:
            raise InventoryValidationError("limit must be between 1 and 1000")
