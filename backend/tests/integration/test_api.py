"""
Integration Tests for API Endpoints
====================================
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.api.main import create_app
from app.core.database import init_db


@pytest_asyncio.fixture
async def app():
    """Create test app with initialized database."""
    app = create_app()
    await init_db()
    return app


@pytest.mark.asyncio
async def test_health_check(app):
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_login_success(app):
    """Test successful login."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(app):
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "wrong"}
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(app):
    """Test protected endpoint without token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(app):
    """Test protected endpoint with valid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]

        # Then access protected endpoint
        response = await client.get(
            "/api/v1/status",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_config(app):
    """Test get configuration endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]

        # Get config
        response = await client.get(
            "/api/v1/config",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "polling_interval" in data
    assert "max_retry_attempts" in data


@pytest.mark.asyncio
async def test_list_errors_empty(app):
    """Test listing errors when none exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]

        # List errors
        response = await client.get(
            "/api/v1/errors",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
