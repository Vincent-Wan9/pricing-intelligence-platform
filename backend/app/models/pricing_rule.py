import uuid
from datetime import datetime
import enum
from sqlalchemy import Boolean, DateTime, String, Text, Enum, text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class RuleType(enum.Enum):
    COST_PLUS = "cost_plus"
    COMPETITOR_BASED = "competitor_based"
    INVENTORY_BASED = "inventory_based"
    DEMAND_BASED = "demand_based"

class PricingRule(Base):
    __tablename__ = "pricing_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    rule_description: Mapped[str] = mapped_column(Text)
    rule_type: Mapped[RuleType] = mapped_column(
        Enum(RuleType, name="rule_type_enum", native_enum=True),
        server_default=text("'cost_plus'"), 
        default=RuleType.COST_PLUS,          
        nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete= "SET NULL"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete= "SET NULL"))
    