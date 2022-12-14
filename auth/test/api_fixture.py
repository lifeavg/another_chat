from datetime import datetime, timedelta, timezone

import pytest

from auth.api.schemas import (AccessTokenData, Login, Permission,
                              SessionTokenData)
from auth.security import create_token
from auth.settings import settings

HOST: str = 'http://localhost:8080'


@pytest.fixture
def authorization(perms: list[str]) -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    access_data = AccessTokenData(jti=1, sub=1, pms=perms, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(
                access_data.dict(),
                settings.security.access_key,
                settings.security.algorithm)}


@pytest.fixture
def session() -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    session_data = SessionTokenData(jti=1, sub=1, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(
                session_data.dict(),
                settings.security.session_key,
                settings.security.algorithm)}


@pytest.fixture
def login():
    return Login(login='user_login', password='pretty_password')


@pytest.fixture
def permission():
    return Permission(name='perm_name', expiration_min=10)
