import uuid
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompetitorProduct(Base):
    __tablename__ = "competitor_products"

    competitor_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id"), nullable=False)
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.competitor_id"), nullable=False)
    competitor_sku: Mapped[str] = mapped_column(String(100), nullable=False)
    competitor_product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    competitor_product_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_crawl_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("product_id", "competitor_id", name="uq_product_competitor"),)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="competitor_product")
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="competitor_product")
    competitor_price: Mapped[list["CompetitorPrice"]] = relationship("CompetitorPrice", back_populates="competitor_product")
