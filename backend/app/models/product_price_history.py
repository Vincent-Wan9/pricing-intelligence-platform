import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductPriceHistory(Base):
    __tablename__ = "product_price_histories"

    history_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("price_recommendations.recommendation_id"), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("idx_product_price_histories", "product_id", "changed_at"),)


    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="product_price_history")
