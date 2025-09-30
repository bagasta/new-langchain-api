from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core import database
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base
from app.models.agent import Agent
from app.services.execution_service import ExecutionService


@pytest.fixture(scope="session")
def _test_engine() -> Generator:
    url = make_url(settings.DATABASE_URL)
    if not url.database:
        raise RuntimeError("DATABASE_URL must include a database name for testing")

    test_db_name = f"{url.database}_test"
    admin_url = url.set(database="postgres")
    test_url = url.set(database=test_db_name)

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    safe_db_name = test_db_name.replace('"', '""')
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"),
            {"name": test_db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{safe_db_name}"'))
    admin_engine.dispose()

    engine = create_engine(
        test_url,
        pool_pre_ping=True,
        poolclass=NullPool,
        future=True,
    )

    vector_available = True
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        except Exception:
            vector_available = False

    if not vector_available and "embeddings" in Base.metadata.tables:
        Base.metadata.remove(Base.metadata.tables["embeddings"])

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.engine = engine
    database.SessionLocal = TestingSessionLocal

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(_test_engine) -> Generator[TestClient, None, None]:
    connection = _test_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session", autouse=True)
def stub_agent_execution() -> Generator[None, None, None]:
    monkeypatch = MonkeyPatch()

    async def _fake_run_agent(
        self: ExecutionService,
        agent: Agent,
        input_text: str,
        parameters,
        session_id,
    ) -> dict:
        return {
            "output": f"{agent.name} responded to: {input_text}",
            "intermediate_steps": [],
            "tools_used": [],
            "execution_time": 0.01,
        }

    monkeypatch.setattr(ExecutionService, "_run_agent", _fake_run_agent)

    yield

    monkeypatch.undo()
