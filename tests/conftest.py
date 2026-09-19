"""Shared pytest fixtures.

Tests run against a throwaway SQLite file so the suite needs no services.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GOLDSEATS_ENV", "test")


@pytest.fixture(scope="session", autouse=True)
def test_database(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"

    from app.core.config import get_settings
    from app.db.base import Base
    from app.db.session import get_engine, get_session_factory

    # Settings and the engine are cached; rebuild them against the temp database.
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    Base.metadata.create_all(get_engine())
    yield db_path


@pytest.fixture
def client(test_database: Path) -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
