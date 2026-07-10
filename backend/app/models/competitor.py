import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    competitor_product: Mapped[list["CompetitorProduct"]] = relationship("CompetitorProduct", back_populates="competitor", cascade="all, delete-orphan")
    crawl_jobs: Mapped["CrawlJob"] = relationship("CrawlJob", back_populates="competitor")