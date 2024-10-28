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
async def test_comprehensive_user_retrieval(client, app):
    # Setup: Register admin and user accounts
    user1 = app.state.user_service.register(
        UserInfo(
            username="user1",
            name="User One",
            birthdate="1990-01-01T00:00:00",
            role=UserRole.USER,
            password="UserPassword123",
        )
    )
    user2 = app.state.user_service.register(
        UserInfo(
            username="user2",
            name="User Two",
            birthdate="1992-02-02T00:00:00",
            role=UserRole.USER,
            password="UserPassword456",
        )
    )
    admin_user = app.state.user_service.register(
        UserInfo(
            username="admin_user",
            name="Admin User",
            birthdate="1980-01-01T00:00:00",
            role=UserRole.ADMIN,
            password="AdminPassword123",
        )
    )

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post(
        f"/user-get?id={user1.uid}&username={user1.info.username}"
    )
    assert response.status_code == 400

    response = await client.post("/user-get")
    assert response.status_code == 400

    response = await client.post(f"/user-get?id={user1.uid}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    response = await client.post(f"/user-get?username={user2.info.username}")
    assert response.status_code == 200
    assert response.json()["username"] == "user2"

    app.dependency_overrides[requires_author] = lambda: user1

    response = await client.post(f"/user-get?id={user1.uid}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    response = await client.post(f"/user-get?username={user1.info.username}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    response = await client.post(f"/user-get?id={user2.uid}")
    assert response.status_code == 500

    response = await client.post(f"/user-get?username={user2.info.username}")
    assert response.status_code == 500

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post("/user-get?username=nonexistent_user")
    assert response.status_code == 404

    response = await client.post("/user-get?id=9999")
    assert response.status_code == 404

    del app.dependency_overrides[requires_author]


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


@pytest.mark.asyncio
async def test_retrieve_user_by_id(client, app):
    response = await client.post(
        "/user-register",
        json={
            "username": "uniqueuser",
            "name": "Unique User",
            "birthdate": "1992-11-11T00:00:00",
            "password": "UniquePassword123",
        },
    )
    assert response.status_code == 200
    user_id = response.json()["uid"]

    app.dependency_overrides[requires_author] = (
        lambda: app.state.user_service.get_by_id(user_id)
    )

    response = await client.post(f"/user-get?id={user_id}")
    assert response.status_code == 200

    del app.dependency_overrides[requires_author]


@pytest.mark.asyncio
async def test_retrieve_user_by_username(client, app):
    response = await client.post(
        "/user-register",
        json={
            "username": "randomuser",
            "name": "Random User",
            "birthdate": "1991-01-01T00:00:00",
            "password": "validPassword987",
        },
    )
    assert response.status_code == 200

    app.dependency_overrides[requires_author] = (
        lambda: app.state.user_service.get_by_username("randomuser")
    )

    response = await client.post("/user-get?username=randomuser")
    assert response.status_code == 200
    assert response.json()["username"] == "randomuser"

    del app.dependency_overrides[requires_author]


@pytest.mark.asyncio
async def test_retrieve_non_existent_user(client, app):
    admin_user = app.state.user_service.register(
        UserInfo(
            username="admin_check",
            name="Admin Checker",
            birthdate="1975-09-09T00:00:00",
            role=UserRole.ADMIN,
            password="CheckerPassword456",
        )
    )

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post("/user-get?username=unknown_user")
    assert response.status_code == 404

    del app.dependency_overrides[requires_author]


@pytest.mark.asyncio
async def test_error_when_both_id_and_username_provided(client, app):
    app.dependency_overrides[requires_author] = lambda: None

    response = await client.post("/user-get?id=123&username=duplicateduser")
    assert response.status_code == 400

    del app.dependency_overrides[requires_author]


@pytest.mark.asyncio
async def test_error_when_neither_id_nor_username_provided(client, app):
    app.dependency_overrides[requires_author] = lambda: None

    response = await client.post("/user-get")
    assert response.status_code == 400

    del app.dependency_overrides[requires_author]


@pytest.mark.asyncio
async def test_direct_admin_granting(app):
    user_service = app.state.user_service
    user_info = {
        "username": "basicuser",
        "name": "Basic User",
        "birthdate": "1985-10-10T00:00:00",
        "password": "BasePassword123",
    }
    user_entity = user_service.register(UserInfo(**user_info))

    user_service.grant_admin(user_entity.uid)

    promoted_user = user_service.get_by_id(user_entity.uid)
    assert promoted_user is not None
    assert promoted_user.info.role == "admin"


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


@pytest.mark.asyncio
async def test_admin_grant_for_non_existent_user(client):
    response = await client.put("/user-promote/9876")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


@pytest.mark.asyncio
async def test_admin_access_user_by_username_success(client, app):
    app.state.user_service.register(
        UserInfo(
            username="testuser100",
            name="Test User",
            birthdate="1990-12-12T00:00:00",
            password="TestPassword123",
        )
    )

    admin_user = app.state.user_service.register(
        UserInfo(
            username="adminuser100",
            name="Admin User",
            birthdate="1980-08-08T00:00:00",
            role=UserRole.ADMIN,
            password="AdminPassword321",
        )
    )

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post("/user-get?username=testuser100")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser100"

    del app.dependency_overrides[requires_author]
