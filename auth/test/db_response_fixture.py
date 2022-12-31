from datetime import datetime, timedelta, timezone

import pytest

from auth.db.models import LoginSession, Permission, Service, User


@pytest.fixture
def user():
    return User(id=1, login='a',
                password='$2b$12$PgOq5lNUhf/Jnyam70ewY.ZDZxU73150IShkznDGjRwNjMZh7H91a',
                confirmed=True, active=True,
                created_timestamp=datetime(2020, 11, 18, 11, 12, 13, 120, timezone.utc))


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


@pytest.fixture
def login_sessions():
    return [
        LoginSession(
            id=1, user_id=1,
            start=datetime.now(timezone.utc) - timedelta(minutes=5),
            end=datetime.now(timezone.utc) + timedelta(minutes=10),
            stopped=False),
        LoginSession(
            id=2, user_id=1,
            start=datetime.now(timezone.utc) - timedelta(minutes=5),
            end=datetime.now(timezone.utc) + timedelta(minutes=10),
            stopped=False)
    ]


@pytest.fixture
def service():
    return Service(id=1, name='service_name', key='service_key')
