import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func, Integer, DateTime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inventory(Base):
    __tablename__ = "inventories"

    inventory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False)
    vendor: Mapped[str] = mapped_column(String(255), nullable=False)
    lead_time: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    on_hand_qty: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.now(), nullable=False)

    # Relationships 
    product: Mapped["Product"] = relationship("Product", back_populates="inventory")