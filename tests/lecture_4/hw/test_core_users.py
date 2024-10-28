import pytest
from lecture_4.demo_service.core.users import (
    UserService,
    UserInfo,
    UserRole,
    password_is_longer_than_8,
)


def test_password_length_check():
    # Меняем пароли для проверки разных сценариев
    assert password_is_longer_than_8("AnotherValidPass") is True
    assert password_is_longer_than_8("tiny") is False


def test_user_registration():
    service = UserService()
    user_info = UserInfo(
        username="newuser",
        name="New User",
        birthdate="1999-05-15T00:00:00",
        password="AnotherValidPassword",
    )
    user = service.register(user_info)
    assert user.uid == 1
    assert user.info.username == "newuser"
    assert user.info.role == UserRole.USER


def test_user_registration_with_existing_username():
    service = UserService()
    user_info = UserInfo(
        username="existinguser",
        name="Existing User",
        birthdate="1995-03-22T00:00:00",
        password="SecurePass123",
    )
    service.register(user_info)
    with pytest.raises(ValueError, match="username is already taken"):
        service.register(user_info)


def test_getting_nonexistent_user():
    service = UserService()
    assert service.get_by_username("unknownuser") is None


def test_admin_role_assignment():
    service = UserService()
    user_info = UserInfo(
        username="testadmin",
        name="Admin Test",
        birthdate="1988-08-08T00:00:00",
        password="StrongAdminPass",
    )
    user = service.register(user_info)
    service.grant_admin(user.uid)
    assert service.get_by_id(user.uid).info.role == UserRole.ADMIN


def test_admin_role_assignment_to_nonexistent_user():
    service = UserService()
    with pytest.raises(ValueError, match="user not found"):
        service.grant_admin(1234)
