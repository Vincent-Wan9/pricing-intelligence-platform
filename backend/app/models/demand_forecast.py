import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    forecast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    forecast_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_demand: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    __table_args__ = (UniqueConstraint("product_id", "forecast_date", "model_name", name="uq_product_date_model"),)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="demand_forecast")