import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Integer, Text, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


from app.core.database import Base

class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.competitor_id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    records_collected: Mapped[int] = mapped_column(Integer, server_default=text("0"), default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    competitor: Mapped["Competitor"] = relationship("Competitor", back_populates="crawl_jobs")
