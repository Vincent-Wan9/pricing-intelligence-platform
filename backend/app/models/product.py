from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func, Integer, text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.category_id"), nullable=False)
    safety_stock: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Pricing
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pricing_rules.rule_id"), nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2),nullable=False)
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    max_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    target_margin: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    auto_pricing_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"), default=False)
   
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(default=func.current_timestamp(), onupdate=func.now())

    # Relationships
    inventories: Mapped[list["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    competitor_product: Mapped[list["CompetitorProduct"]] = relationship("CompetitorProduct", back_populates="product")
    product_price_history: Mapped[list["ProductPriceHistory"]] = relationship("ProductPriceHistory", back_populates="product", cascade="all, delete-orphan")
    pricing_rule: Mapped["PricingRule"] = relationship("PricingRule")
    demand_forecast: Mapped[list["DemandForecast"]] = relationship("DemandForecast", back_populates="product")
    demand_history: Mapped[list["DemandHistory"]] = relationship(
        "DemandHistory", back_populates="product", cascade="all, delete-orphan"
    )

    price_recommendation: Mapped[list["PriceRecommendation"]] = relationship("PriceRecommendation", back_populates="product", cascade="all, delete-orphan")

    

    
