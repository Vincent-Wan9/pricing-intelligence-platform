from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using them
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False