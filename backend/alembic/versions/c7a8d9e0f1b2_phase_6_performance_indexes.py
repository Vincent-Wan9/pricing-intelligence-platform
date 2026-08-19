"""add phase 6 performance indexes

Revision ID: c7a8d9e0f1b2
Revises: f5c1a9d47021
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c7a8d9e0f1b2"
down_revision: Union[str, Sequence[str], None] = "f5c1a9d47021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_competitor_products_competitor_id",
        "competitor_products",
        ["competitor_id"],
        unique=False,
    )
    op.create_index(
        "ix_inventories_product_id",
        "inventories",
        ["product_id"],
        unique=True,
    )
    op.create_index(
        "ix_price_recommendations_product_generated",
        "price_recommendations",
        ["product_id", "generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_price_recommendations_product_generated",
        table_name="price_recommendations",
    )
    op.drop_index("ix_inventories_product_id", table_name="inventories")
    op.drop_index(
        "ix_competitor_products_competitor_id",
        table_name="competitor_products",
    )
