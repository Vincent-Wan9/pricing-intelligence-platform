from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.inventory import Inventory
from app.schemas.inventory_schema import CreateInventorySchema, UpdateInventorySchema


class InventoryCRUD(CRUDBase[Inventory, CreateInventorySchema, UpdateInventorySchema]):

    def get_by_product(self, db: Session, product_id: UUID):
        stmt = (select(Inventory).where(Inventory.product_id == product_id))

        return db.scalar(stmt)

    def get_low_stock(self, db: Session, threshold: int):
        stmt = (select(Inventory).where(Inventory.quantityon_hand_qty_on_hand <= threshold)
            .order_by(Inventory.on_hand_qty))

        return list(db.scalars(stmt).all())

    def get_out_of_stock(self, db: Session):
        stmt = (select(Inventory).where(Inventory.on_hand_qty == 0))

        return list(db.scalars(stmt).all())


inventory_crud = InventoryCRUD(Inventory)