"""
Pytest Configuration and Fixtures
=================================
"""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator

# Set test database URL before importing app modules
import tempfile
import sys

_test_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
os.environ["OAS_DATABASE_URL"] = f"sqlite:///{_test_db_file.name}"
_test_db_file.close()

# Remove cached modules to ensure fresh import with test config
for mod in list(sys.modules.keys()):
    if mod.startswith('app.'):
        del sys.modules[mod]

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models.base import Base
from app.core.config import Settings, get_settings
from app.api.main import create_app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        debug=True,
    )


@pytest_asyncio.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_client():
    """Create a test HTTP client."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_git_repo(mocker):
    """Mock a git repository."""
    mock_repo = mocker.MagicMock()
    mock_repo.head.commit.hexsha = "abc123def456"
    mock_repo.remotes = {"origin": mocker.MagicMock()}
    mock_repo.git.diff.return_value = ""
    return mock_repo


@pytest.fixture
def sample_error_data():
    """Sample error data for testing."""
    return {
        "error_type": "ImportError",
        "message": "No module named 'missing_module'",
        "module_name": "sale_custom",
        "file_path": "/home/odoo/custom_addons/sale_custom/models/sale.py",
        "line_number": 42,
        "stack_trace": """Traceback (most recent call last):
  File "/home/odoo/custom_addons/sale_custom/models/sale.py", line 42, in <module>
    from missing_module import something
ImportError: No module named 'missing_module'
""",
    }


@pytest.fixture
def sample_log_content():
    """Sample Odoo log content for testing."""
    return """
2024-11-23 10:30:00,123 12345 INFO odoo Starting service
2024-11-23 10:30:01,234 12345 INFO odoo Database connected
2024-11-23 10:30:05,345 12345 ERROR odoo.modules Traceback (most recent call last):
  File "/home/odoo/custom_addons/sale_custom/models/sale.py", line 42, in <module>
    from missing_module import something
ImportError: No module named 'missing_module'
2024-11-23 10:30:06,456 12345 INFO odoo Continuing...
"""
