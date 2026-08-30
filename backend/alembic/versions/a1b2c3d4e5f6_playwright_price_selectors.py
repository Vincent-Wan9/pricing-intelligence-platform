"""add mapping-specific Playwright price selectors

Revision ID: a1b2c3d4e5f6
Revises: e6f7a8b9c0d1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("competitor_products", sa.Column("price_selector", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("competitor_products", "price_selector")
