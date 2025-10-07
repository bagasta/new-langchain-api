from sqlalchemy import create_engine, inspect
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


def _ensure_agents_table_schema(connection) -> None:
    """Backfill agent columns that may pre-date newer migrations."""
    inspector = inspect(connection)
    if "agents" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("agents")}
    dialect = engine.url.get_backend_name()

    statements = []

    if "mcp_servers" not in existing_columns:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE agents ADD COLUMN mcp_servers JSONB NOT NULL DEFAULT '{}'::jsonb"
            )
        else:
            statements.append(
                "ALTER TABLE agents ADD COLUMN mcp_servers TEXT NOT NULL DEFAULT '{}'"
            )

    if "allowed_tools" not in existing_columns:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE agents ADD COLUMN allowed_tools TEXT[] NOT NULL DEFAULT '{}'::text[]"
            )
        else:
            statements.append(
                "ALTER TABLE agents ADD COLUMN allowed_tools TEXT NOT NULL DEFAULT '[]'"
            )

    for statement in statements:
        connection.exec_driver_sql(statement)
        logger.info(
            "Applied schema patch for agents table",
            statement=statement,
        )


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
        _ensure_agents_table_schema(connection)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
