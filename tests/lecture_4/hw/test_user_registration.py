import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from lecture_4.demo_service.api.main import create_app
from lecture_4.demo_service.api.utils import initialize, requires_author
from lecture_4.demo_service.core.users import UserInfo, UserRole


@pytest_asyncio.fixture
async def app():
    app = create_app()
    app.dependency_overrides[requires_author] = lambda: None
    async with initialize(app):
        yield app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_successful_user_registration(client):
    response = await client.post(
        "/user-register",
        json={
            "username": "sampleuser",
            "name": "Sample User",
            "birthdate": "1988-05-15T00:00:00",
            "password": "samplePassword123",
        },
    )
    assert response.status_code == 200
    assert response.json()["username"] == "sampleuser"


@pytest.mark.asyncio
async def test_user_registration_with_invalid_password(client):
    response = await client.post(
        "/user-register",
        json={
            "username": "quickuser",
            "name": "Quick User",
            "birthdate": "1990-07-07T00:00:00",
            "password": "short",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid password"


@pytest.mark.asyncio
async def test_registration_with_existing_username(client):
    await client.post(
        "/user-register",
        json={
            "username": "sampleuser",
            "name": "Sample User",
            "birthdate": "1988-05-15T00:00:00",
            "password": "samplePassword123",
        },
    )
    response = await client.post(
        "/user-register",
        json={
            "username": "sampleuser",
            "name": "Another User",
            "birthdate": "1985-02-02T00:00:00",
            "password": "differentPassword123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "username is already taken"
