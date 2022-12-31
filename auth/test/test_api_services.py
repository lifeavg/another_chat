import pytest
from api_fixture import HOST, authorization, permission
from db_response_fixture import permissions, service
from httpx import AsyncClient
from pytest_mock import mocker

import auth
from auth.api.routers.app import app
from auth.api.routers.exception import IntegrityError
from auth.api.schemas import Key, Permission, Service

BASE_URL: str = HOST + '/services'


class TestCreateService:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization):
        mocker.patch(
            'auth.api.base.commit_if_not_exists')
        mocker.patch(
            'auth.security.new_key_validator',
            return_value=(True, 'OK'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post('/', json=Service(name='s', key='k').dict())
        assert response.status_code == 201

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_exists(self, mocker, authorization):
        mocker.patch(
            'auth.api.base.commit_if_not_exists',
            side_effect=IntegrityError('DETAIL: name'))
        mocker.patch(
            'auth.security.new_key_validator',
            return_value=(True, 'OK'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post('/', json=Service(name='s', key='k').dict())
        assert response.status_code == 409
        assert response.json() == {'detail': 'name'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_invalid_key(self, mocker, authorization):
        mocker.patch(
            'auth.api.base.commit_if_not_exists')
        mocker.patch(
            'auth.security.new_key_validator',
            return_value=(False, 'REASON'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post('/', json=Service(name='s', key='k').dict())
        assert response.status_code == 409
        assert response.json() == {'detail': 'REASON'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, mocker, authorization):
        mocker.patch(
            'auth.api.base.commit_if_not_exists')
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post('/', json=Service(name='s', key='k').dict())
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}
        auth.api.base.commit_if_not_exists.assert_not_called()  # type: ignore


class TestServiceData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, service):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=service)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/' + service.name)
        assert response.status_code == 200
        assert response.json() == Service(name=service.name, key=service.key).dict()

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.service_by_name',
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


class TestAddServicePermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, service, permission):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=service)
        mocker.patch(
            'auth.api.base.commit_if_not_exists')
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post(
                '/' + service.name + '/permissions',
                json=permission.dict())
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_exists(self, mocker, authorization, service, permission):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=service)
        mocker.patch(
            'auth.api.base.commit_if_not_exists',
            side_effect=IntegrityError(f'DETAIL: {service.name}'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post(
                '/' + service.name + '/permissions',
                json=permission.dict())
        assert response.status_code == 409
        assert (response.json() == {'detail': service.name})

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization, service, permission):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.post(
                '/' + service.name + '/permissions',
                json=permission.dict())
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestServicePermissions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_ok(self, mocker, authorization, permissions):
        mocker.patch(
            'auth.db.query.service_permissions',
            return_value=permissions)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/service_name/permissions')
        assert response.status_code == 200
        assert response.json() == [
            Permission(name=permissions[0].name,
                       expiration_min=permissions[0].expiration_min),
            Permission(name=permissions[1].name,
                       expiration_min=permissions[1].expiration_min)]

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_empty(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.service_permissions',
            return_value=[])
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/service_name/permissions')
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/service_name/permissions')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestUpdateServiceKey:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_ok(self, mocker, authorization, service):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=service)
        mocker.patch(
            'auth.security.new_key_validator',
            return_value=(True, 'OK'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/' + service.name, json=Key(key='new_key1').dict())
        assert response.status_code == 200
        assert service.key == 'new_key1'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/name', json=Key(key='new_key1').dict())
        assert response.status_code == 404
        assert response.json() == {'detail': ['name']}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_mod'],])
    async def test_invalid_key(self, mocker, authorization, service):
        mocker.patch(
            'auth.db.query.service_by_name',
            return_value=service)
        mocker.patch(
            'auth.security.new_key_validator',
            return_value=(False, 'REASON'))
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/' + service.name, json=Key(key='new_key1').dict())
        assert response.status_code == 409
        assert service.key != 'new_key1'
        assert response.json() == {'detail': 'REASON'}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization, service):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.put('/' + service.name, json=Key(key='new_key1').dict())
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestDeleteService:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, service):
        mocker.patch(
            'auth.db.query.service_delete',
            return_value=service.name)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.delete('/' + service.name)
        assert response.status_code == 204

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization, service):
        mocker.patch(
            'auth.db.query.service_delete',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.delete('/' + service.name)
        assert response.status_code == 404
        assert response.json() == {'detail': [service.name]}
