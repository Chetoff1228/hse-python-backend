import pytest
from http import HTTPStatus
from fastapi import FastAPI, HTTPException
from lecture_4.demo_service.api.utils import (
    initialize,
    user_service,
    requires_author,
    requires_admin,
    value_error_handler,
)
from lecture_4.demo_service.core.users import UserService, UserInfo, UserRole
from fastapi.security import HTTPBasicCredentials
from datetime import datetime
from starlette.requests import Request


@pytest.fixture
def app():
    app = FastAPI()
    app.state.user_service = UserService(password_validators=[])
    return app


@pytest.fixture
async def setup_user_service(app: FastAPI):
    async with initialize(app):
        yield


@pytest.mark.asyncio
async def test_value_error_handler():
    app = FastAPI()
    request = Request(scope={"type": "http", "method": "GET", "path": "/"})
    response = await value_error_handler(request, ValueError("Test error"))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    response_content = response.body.decode()
    assert "Test error" in response_content


def test_user_service_initialization(setup_user_service, app):
    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    assert isinstance(service, UserService)


def test_authorization_with_valid_credentials(setup_user_service, app):
    username = "user"
    password = "Password123"

    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    service.register(
        UserInfo(
            username=username,
            name="User Name",
            birthdate=datetime(2000, 1, 1),
            role=UserRole.USER,
            password=password,
        )
    )
    credentials = HTTPBasicCredentials(username=username, password=password)
    user_entity = requires_author(credentials, service)
    assert user_entity.info.username == username


def test_authorization_with_invalid_password(setup_user_service, app):
    username = "user"
    valid_password = "Password123"
    invalid_password = "WrongPassword"

    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    service.register(
        UserInfo(
            username=username,
            name="User Name",
            birthdate=datetime(2000, 1, 1),
            role=UserRole.USER,
            password=valid_password,
        )
    )
    credentials = HTTPBasicCredentials(username=username, password=invalid_password)
    with pytest.raises(HTTPException) as exc_info:
        requires_author(credentials, service)
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_authorization_with_nonexistent_user(setup_user_service, app):
    non_existent_username = "nonexistent"
    password = "Password123"

    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    credentials = HTTPBasicCredentials(
        username=non_existent_username, password=password
    )
    with pytest.raises(HTTPException) as exc_info:
        requires_author(credentials, service)
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_admin_access_with_valid_admin_user(setup_user_service, app):
    username = "admin"
    password = "AdminPassword123"
    role = UserRole.ADMIN

    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    admin_info = UserInfo(
        username=username,
        name="Admin User",
        birthdate=datetime(1990, 1, 1),
        role=role,
        password=password,
    )
    admin_entity = service.register(admin_info)

    admin = requires_admin(admin_entity)
    assert admin.info.username == username


def test_admin_access_with_regular_user(setup_user_service, app):
    username = "user"
    password = "UserPassword123"
    role = UserRole.USER

    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    user_info = UserInfo(
        username=username,
        name="Regular User",
        birthdate=datetime(2000, 1, 1),
        role=role,
        password=password,
    )
    user_entity = service.register(user_info)
    with pytest.raises(HTTPException) as exc_info:
        requires_admin(user_entity)
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
