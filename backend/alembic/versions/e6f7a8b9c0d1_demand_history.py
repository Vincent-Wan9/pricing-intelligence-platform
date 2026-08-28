"""add historical product demand

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demand_history",
        sa.Column("demand_history_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("demand_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("demand_history_id"),
        sa.UniqueConstraint("product_id", "demand_date", name="uq_demand_history_product_date"),
        sa.CheckConstraint("quantity >= 0", name="ck_demand_history_quantity_nonnegative"),
    )
    op.create_index("ix_demand_history_product_date", "demand_history", ["product_id", "demand_date"])


def downgrade() -> None:
    op.drop_index("ix_demand_history_product_date", table_name="demand_history")
    op.drop_table("demand_history")
