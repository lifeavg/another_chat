from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from pytest_mock import mocker

from auth.api.routers.app import app
from auth.api.schemas import AccessTokenData
from auth.db.models import Permission, User
from auth.security import SEC_SECRET_ACCESS, create_token

BASE_URL: str = 'http://localhost:8080/users'


@pytest.fixture
def authorization(permissions: list[str]) -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    access_data = AccessTokenData(jti=1, sub=1, pms=permissions, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(access_data.dict(), SEC_SECRET_ACCESS)}


@pytest.fixture
def user():
    return User(id=1, login='a', password='b', confirmed=True, active=True,
                created_timestamp=datetime(2020, 11, 18, 11, 12, 13, 120, timezone.utc))


@pytest.fixture
def user_with_permissions():
    return User(id=1, login='a', password='b', confirmed=True, active=True,
                created_timestamp=datetime(
                    2020, 11, 18, 11, 12, 13, 120, timezone.utc),
                permissions=[
                    Permission(id=5, name='p1', service_id=2,
                               expiration_min=10),
                    Permission(id=6, name='p2', service_id=3,
                               expiration_min=10)
                ])


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth_inf_user'],])
async def test_user_data_ok(mocker, authorization, user):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=user)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1')
    assert response.status_code == 200
    assert response.json() == {'id': 1, 'login': 'a', 'confirmed': True,
                               'created_timestamp': user.created_timestamp.isoformat()}


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth_inf_user'],])
async def test_user_data_not_found(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1')
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth'],])
async def test_user_data_no_permission(authorization):
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1')
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth_adm'],])
async def test_user_permissions_ok(mocker, user_with_permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=user_with_permissions)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1/permissions')
    assert response.status_code == 200
    assert response.json() == [
        perm.name for perm in user_with_permissions.permissions]


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth_adm'],])
async def test_user_permissions_not_found(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1/permissions')
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}


@pytest.mark.asyncio
@pytest.mark.parametrize('permissions', [['auth'],])
async def test_user_permissions_no_permission(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1/permissions')
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}
