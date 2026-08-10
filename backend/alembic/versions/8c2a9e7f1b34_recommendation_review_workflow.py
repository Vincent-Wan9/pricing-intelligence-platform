"""add recommendation review workflow

Revision ID: 8c2a9e7f1b34
Revises: 570d517ff64c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8c2a9e7f1b34"
down_revision: Union[str, Sequence[str], None] = "570d517ff64c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("price_recommendations", sa.Column("status", sa.String(length=20), server_default="pending", nullable=False))
    op.add_column("price_recommendations", sa.Column("reviewed_by", sa.UUID(), nullable=True))
    op.add_column("price_recommendations", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("price_recommendations", sa.Column("review_reason", sa.Text(), nullable=True))
    op.add_column("price_recommendations", sa.Column("current_price", sa.Numeric(10, 2), nullable=True))
    op.execute("UPDATE price_recommendations r SET current_price = p.current_price FROM products p WHERE r.product_id = p.product_id")
    op.alter_column("price_recommendations", "current_price", nullable=False)
    op.add_column("price_recommendations", sa.Column("applied_by", sa.UUID(), nullable=True))
    op.add_column("price_recommendations", sa.Column("applied_at", sa.DateTime(), nullable=True))
    op.add_column("product_price_histories", sa.Column("change_reason", sa.Text(), server_default="Price changed", nullable=False))
    op.add_column("product_price_histories", sa.Column("recommendation_id", sa.UUID(), nullable=True))
    op.add_column("product_price_histories", sa.Column("changed_by", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_price_recommendations_reviewed_by_users", "price_recommendations", "users", ["reviewed_by"], ["user_id"], ondelete="SET NULL")
    op.create_foreign_key("fk_price_recommendations_applied_by_users", "price_recommendations", "users", ["applied_by"], ["user_id"], ondelete="SET NULL")
    op.create_foreign_key("fk_price_history_recommendation", "product_price_histories", "price_recommendations", ["recommendation_id"], ["recommendation_id"])
    op.create_foreign_key("fk_price_history_changed_by_users", "product_price_histories", "users", ["changed_by"], ["user_id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_price_history_changed_by_users", "product_price_histories", type_="foreignkey")
    op.drop_constraint("fk_price_history_recommendation", "product_price_histories", type_="foreignkey")
    op.drop_constraint("fk_price_recommendations_applied_by_users", "price_recommendations", type_="foreignkey")
    op.drop_constraint("fk_price_recommendations_reviewed_by_users", "price_recommendations", type_="foreignkey")
    op.drop_column("price_recommendations", "review_reason")
    op.drop_column("price_recommendations", "reviewed_at")
    op.drop_column("price_recommendations", "reviewed_by")
    op.drop_column("price_recommendations", "status")
    op.drop_column("price_recommendations", "applied_at")
    op.drop_column("price_recommendations", "applied_by")
    op.drop_column("price_recommendations", "current_price")
    op.drop_column("product_price_histories", "changed_by")
    op.drop_column("product_price_histories", "recommendation_id")
    op.drop_column("product_price_histories", "change_reason")
