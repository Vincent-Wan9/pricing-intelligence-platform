import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    price_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitor_products.competitor_product_id"), nullable=False)
    competitor_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean)
    crawl_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("idx_competitor_prices", "competitor_product_id", "crawl_timestamp"),)
    
    # Relationships
    competitor_product: Mapped["CompetitorProduct"] = relationship("CompetitorProduct", back_populates="competitor_price")
    