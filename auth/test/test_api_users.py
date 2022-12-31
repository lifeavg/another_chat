from unittest.mock import MagicMock

import pytest
from api_fixture import HOST, authorization, login
from db_response_fixture import permissions, user, user_with_permissions
from httpx import AsyncClient
from pytest_mock import mocker

import auth
from auth.api.routers.app import app
from auth.security import verify_password

BASE_URL: str = HOST + '/users'


class TestUserData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_inf_user'],])
    async def test_ok(self, mocker, authorization, user):
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
    async def test_not_found(self, mocker, authorization):
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
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestUserPermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, user_with_permissions, authorization):
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
    async def test_not_found(self, mocker, authorization):
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
    async def test_no_permission(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.user_with_permissions',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1/permissions')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestAddUserPermission:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_add_user_permissions_ok(self, mocker, user_with_permissions, permissions, authorization):
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
    async def test_no_permission(self, authorization, permissions):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.post('/1/permissions/add', json=[p.name for p in permissions])
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_no_user(self, mocker, permissions, authorization):
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
    async def test_not_found(self, mocker, permissions, authorization, user_with_permissions):
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
        assert set(response.json()['detail']) == set(
            [p.name for p in permissions])


class TestRemoveUserPermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_dont_have(self, mocker, user_with_permissions, permissions, authorization):
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
    async def test_no_permission(self, authorization, permissions):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.post('/1/permissions/remove', json=[p.name for p in permissions])
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_no_user(self, mocker, permissions, authorization):
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
    async def test_not_found(self, mocker, permissions, authorization, user_with_permissions):
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
        assert set(response.json()['detail']) == set(
            [p.name for p in permissions])


class TestUpdateUserState:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, user, authorization):
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
    async def test_no_parameter(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.put('/1')
        assert response.status_code == 400
        assert response.json() == {'detail': 'Specify at least one parameter'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.user_by_id',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.put('/1?confirmed=False&active=False')
        assert response.status_code == 404
        assert response.json() == {'detail': [1,]}


class TestUpdateUserData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_upd_user'],])
    async def test_ok(self, mocker, user, authorization, login):
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
        auth.security.new_password_validator.assert_called_with(  # type: ignore
            login.password)
        auth.api.base.commit_if_not_exists.assert_called()  # type: ignore

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_upd_user'],])
    async def test_invalid_password(self, mocker, user, authorization, login):
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
        auth.security.new_password_validator.assert_called_with(  # type: ignore
            login.password)
        auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_upd_user'],])
    async def test_invalid_not_found(self, mocker, authorization, login):
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
    async def test_invalid_no_permission(self, mocker, authorization, login):
        mocker.patch(
            'auth.api.base.commit_if_not_exists')
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.post('/1/update', json=login.dict())
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}
        auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore


class TestDeleteUser:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_del_user'],])
    async def test_delete_user_ok(self, mocker, authorization):
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
    async def test_not_found(self, mocker, authorization):
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
    async def test_no_permission(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.user_delete',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization,) as ac:
            response = await ac.delete('/1')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}
        auth.db.query.user_delete.assert_not_called()  # type: ignore
