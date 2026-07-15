from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_db():
    """Mock async database session"""
    db = AsyncMock()
    return db


@pytest.fixture
def anyio_backend():
    return "asyncio"
