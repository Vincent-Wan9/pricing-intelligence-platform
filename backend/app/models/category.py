from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base



class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Self-Referencing Foreign Key
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (CheckConstraint("category_id <> parent_id", name="chk_no_self_reference"),)