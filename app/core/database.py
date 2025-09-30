from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.base import Base
from app.core.logging import logger


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=NullPool,
    echo=settings.LOG_LEVEL == "DEBUG",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialise database extensions and tables."""
    with engine.begin() as connection:
        if engine.url.get_backend_name() == "postgresql":
            try:
                connection.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "vector"')
            except ProgrammingError as exc:
                logger.warning(
                    "Unable to ensure pgvector extension; verify it exists and the role has permission.",
                    error=str(exc)
                )
        Base.metadata.create_all(bind=connection)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
