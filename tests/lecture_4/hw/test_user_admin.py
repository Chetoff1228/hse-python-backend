import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from lecture_4.demo_service.api.main import create_app
from lecture_4.demo_service.api.utils import initialize, requires_author
from lecture_4.demo_service.core.users import UserInfo, UserRole


@pytest_asyncio.fixture
async def app():
    app = create_app()
    async with initialize(app):
        yield app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_admin_promotion_via_endpoint(client, app):
    admin_user = app.state.user_service.register(
        UserInfo(
            username="superadmin",
            name="Super Admin",
            birthdate="1981-03-03T00:00:00",
            role=UserRole.ADMIN,
            password="SuperAdminPassword456",
        )
    )

    user = app.state.user_service.register(
        UserInfo(
            username="regularuser",
            name="Regular User",
            birthdate="1993-04-04T00:00:00",
            role=UserRole.USER,
            password="UserPassword789",
        )
    )

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post(f"/user-promote?id={user.uid}")
    assert response.status_code == 200

    promoted_user = app.state.user_service.get_by_id(user.uid)
    assert promoted_user is not None
    assert promoted_user.info.role == "admin"

    del app.dependency_overrides[requires_author]
