"""SQLAlchemy engine, session factory, declarative base, and the FastAPI DB dependency."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# SQLite (tests) needs check_same_thread off and StaticPool so an in-memory DB is one shared
# connection across sessions; Postgres uses pool_pre_ping like Guide.
_url = settings.sqlalchemy_url
if _url.startswith("sqlite"):
    engine = create_engine(_url, echo=settings.DEBUG, future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    engine = create_engine(_url, pool_pre_ping=True, echo=settings.DEBUG)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base shared by every LucaCredit ORM model."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
