from datetime import datetime, timezone

import pytest

from auth.api.schemas import Login
from auth.db.models import Permission, User


@pytest.fixture
def user():
    return User(id=1, login='a', password='b', confirmed=True, active=True,
                created_timestamp=datetime(2020, 11, 18, 11, 12, 13, 120, timezone.utc))


@pytest.fixture
def login():
    return Login(login='user_login', password='pretty_password')


@pytest.fixture
def user_with_permissions():
    # def append(*arg):
    #     pass
    user = User(id=1, login='a', password='b', confirmed=True, active=True,
                created_timestamp=datetime(
                    2020, 11, 18, 11, 12, 13, 120, timezone.utc),
                permissions=[
                    Permission(id=5, name='p1', service_id=2,
                               expiration_min=10),
                    Permission(id=6, name='p2', service_id=3,
                               expiration_min=10)
                ])
    # user.permissions.append = append.__get__(user.permissions)
    return user


@pytest.fixture
def permissions():
    return [Permission(id=7, name='p7', service_id=3, expiration_min=10),
            Permission(id=8, name='p8', service_id=5, expiration_min=10)]
