from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.product import Product
from app.schemas.product_schema import CreateProductSchema, UpdateProductSchema


class ProductCRUD(CRUDBase[Product, CreateProductSchema, UpdateProductSchema]):

    def get_by_sku(self, db: Session, sku: str):
        stmt = (select(Product).where(Product.sku == sku))

        return db.scalar(stmt)

    def get_by_name(self, db: Session, name: str):
        stmt = (select(Product).where(Product.product_name == name))

        return db.scalar(stmt)

    def get_by_category(self, db: Session, category_id: UUID):
        stmt = (select(Product).where(Product.category_id == category_id))

        return list(db.scalars(stmt).all())

    def get_active_products(self, db: Session):
        stmt = (select(Product).where(Product.is_active == True).order_by(Product.product_name))

        return list(db.scalars(stmt).all())


product_crud = ProductCRUD(Product)