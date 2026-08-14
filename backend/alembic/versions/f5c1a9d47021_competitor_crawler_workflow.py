"""add competitor crawler workflow fields

Revision ID: f5c1a9d47021
Revises: 8c2a9e7f1b34
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f5c1a9d47021"
down_revision: Union[str, Sequence[str], None] = "8c2a9e7f1b34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("competitor_products", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("competitor_products", sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("competitor_products", sa.Column("last_crawl_error", sa.Text(), nullable=True))
    op.add_column("competitor_prices", sa.Column("crawl_job_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_competitor_prices_crawl_job", "competitor_prices", "crawl_jobs",
        ["crawl_job_id"], ["job_id"], ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_crawl_job_competitor_product", "competitor_prices",
        ["crawl_job_id", "competitor_product_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_crawl_job_competitor_product", "competitor_prices", type_="unique")
    op.drop_constraint("fk_competitor_prices_crawl_job", "competitor_prices", type_="foreignkey")
    op.drop_column("competitor_prices", "crawl_job_id")
    op.drop_column("competitor_products", "is_active")
    op.drop_column("competitor_products", "last_crawl_error")
    op.drop_column("competitor_products", "last_crawled_at")
