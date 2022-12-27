from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from pytest_mock import mocker

import auth
from auth.api.routers.app import app
from auth.api.schemas import AccessTokenData, Login
from auth.db.models import Permission, User
from auth.security import SEC_SECRET_ACCESS, create_token, verify_password

BASE_URL: str = 'http://localhost:8080/users'


@pytest.fixture
def authorization(perms: list[str]) -> dict[str, str]:
    token_exp = datetime.now(timezone.utc) + timedelta(days=2)
    access_data = AccessTokenData(jti=1, sub=1, pms=perms, exp=token_exp)
    return {'Authorization': 'Bearer ' +
            create_token(access_data.dict(), SEC_SECRET_ACCESS)}


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


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_inf_user'],])
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
@pytest.mark.parametrize('perms', [['auth_inf_user'],])
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
@pytest.mark.parametrize('perms', [['auth'],])
async def test_user_data_no_permission(authorization):
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1')
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
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
@pytest.mark.parametrize('perms', [['auth_adm'],])
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
@pytest.mark.parametrize('perms', [['auth'],])
async def test_user_permissions_no_permission(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization) as ac:
        response = await ac.get('/1/permissions')
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_add_user_permissions_ok(mocker, user_with_permissions, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=user_with_permissions)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=permissions)
    user_with_permissions.permissions.append = MagicMock()
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/add', json=[p.name for p in permissions])
    assert response.status_code == 200
    user_with_permissions.permissions.append.assert_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_info'],])
async def test_add_user_permissions_no_permission(authorization, permissions):
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/add', json=[p.name for p in permissions])
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_add_user_permissions_no_user(mocker, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=None)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=permissions)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/add', json=[p.name for p in permissions])
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_add_user_permissions_not_found(mocker, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=user_with_permissions)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=set())
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/add', json=[p.name for p in permissions])
    assert response.status_code == 404
    assert set(response.json()['detail']) == set([p.name for p in permissions])


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_remove_user_permissions_dont_have(mocker, user_with_permissions, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=user_with_permissions)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=permissions)
    user_with_permissions.permissions.remove = MagicMock()
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/remove', json=[p.name for p in permissions])
    assert response.status_code == 200
    user_with_permissions.permissions.remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_info'],])
async def test_remove_user_permissions_no_permission(authorization, permissions):
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/remove', json=[p.name for p in permissions])
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_remove_user_permissions_no_user(mocker, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=None)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=permissions)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/remove', json=[p.name for p in permissions])
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_remove_user_permissions_not_found(mocker, permissions, authorization):
    mocker.patch(
        'auth.db.query.user_with_permissions',
        return_value=user_with_permissions)
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=set())
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/permissions/remove', json=[p.name for p in permissions])
    assert response.status_code == 404
    assert set(response.json()['detail']) == set([p.name for p in permissions])


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_update_user_state_ok(mocker, user, authorization):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=user)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.put('/1?confirmed=False&active=False')
    assert response.status_code == 200
    assert user.confirmed == False
    assert user.active == False


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_update_user_state_no_parameter(authorization):
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.put('/1')
    assert response.status_code == 400
    assert response.json() == {'detail': 'Specify at least one parameter'}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_adm'],])
async def test_update_user_state_not_found(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.put('/1?confirmed=False&active=False')
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_upd_user'],])
async def test_update_user_data_ok(mocker, user, authorization, login):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=user)
    mocker.patch(
        'auth.security.new_password_validator',
        return_value=(True, 'OK'))
    mocker.patch(
        'auth.api.base.commit_if_not_exists')
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/update', json=login.dict())
    assert response.status_code == 200
    assert user.login == login.login
    assert verify_password(login.password, user.password) == True
    auth.security.new_password_validator.assert_called_with( # type: ignore
        login.password)
    auth.api.base.commit_if_not_exists.assert_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_upd_user'],])
async def test_update_user_data_invalid_password(mocker, user, authorization, login):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=user)
    mocker.patch(
        'auth.security.new_password_validator',
        return_value=(False, 'REASON'))
    mocker.patch(
        'auth.api.base.commit_if_not_exists')
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/update', json=login.dict())
    assert response.status_code == 409
    assert response.json() == {'detail': 'REASON'}
    auth.security.new_password_validator.assert_called_with( # type: ignore
        login.password)  
    auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_upd_user'],])
async def test_update_user_data_invalid_not_found(mocker, authorization, login):
    mocker.patch(
        'auth.db.query.user_by_id',
        return_value=None)
    mocker.patch(
        'auth.api.base.commit_if_not_exists')
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/update', json=login.dict())
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}
    auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_upd'],])
async def test_update_user_data_invalid_no_permission(mocker, authorization, login):
    mocker.patch(
        'auth.api.base.commit_if_not_exists')
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.post('/1/update', json=login.dict())
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}
    auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_del_user'],])
async def test_delete_user_ok(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_delete',
        return_value=1)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.delete('/1')
    assert response.status_code == 204
    auth.db.query.user_delete.assert_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_del_user'],])
async def test_delete_user_not_found(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_delete',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.delete('/1')
    assert response.status_code == 404
    assert response.json() == {'detail': [1,]}
    auth.db.query.user_delete.assert_called()  # type: ignore


@pytest.mark.asyncio
@pytest.mark.parametrize('perms', [['auth_del'],])
async def test_delete_user_no_permission(mocker, authorization):
    mocker.patch(
        'auth.db.query.user_delete',
        return_value=None)
    async with AsyncClient(
            app=app, base_url=BASE_URL, headers=authorization,) as ac:
        response = await ac.delete('/1')
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid authorization code: type'}
    auth.db.query.user_delete.assert_not_called()  # type: ignore
