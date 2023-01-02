import pytest
from api_fixture import HOST, authorization
from db_response_fixture import permission as permission_md
from db_response_fixture import permissions
from httpx import AsyncClient
from pytest_mock import mocker

from auth.api.schemas import Permission
from auth.main import app

BASE_URL: str = HOST + '/permissions'


class TestPermissionData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_ok(self, mocker, authorization, permission_md):
        mocker.patch(
            'auth.db.query.permission_by_name',
            return_value=permission_md)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/' + permission_md.name)
        assert response.status_code == 200
        assert response.json() == Permission(name=permission_md.name,
                                             expiration_min=permission_md.expiration_min)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.permission_by_name',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/name')
        assert response.status_code == 404
        assert response.json() == {'detail': ['name']}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/name')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestDeleteServicePermission:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.permission_delete',
            return_value='permission_name')
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.delete('/permission_name')
        assert response.status_code == 204

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.permission_delete',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.delete('/permission_name')
        assert response.status_code == 404
        assert response.json() == {'detail': ['permission_name']}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.delete('/permission_name')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestUpdateExpirationTime:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_ok(self, mocker, authorization, permission_md):
        mocker.patch(
            'auth.db.query.permission_by_name',
            return_value=permission_md)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/' + permission_md.name + '?exp=15')
        assert response.status_code == 200
        assert permission_md.expiration_min == 15

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.permission_by_name',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/permission_name?exp=15')
        assert response.status_code == 404
        assert response.json() == {'detail': ['permission_name']}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/permission_name?exp=15')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}
