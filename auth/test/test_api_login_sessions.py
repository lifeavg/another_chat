import pytest
from api_fixture import HOST, authorization
from db_response_fixture import access_sessions, login_session
from httpx import AsyncClient
from pytest_mock import mocker

from auth.api.routers.app import app

BASE_URL: str = HOST + '/login_sessions'


class TestPermissionData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, login_session):
        mocker.patch(
            'auth.db.query.login_session_by_id',
            return_value=login_session)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get(f'/{login_session.id}')
        assert response.status_code == 200
        assert (response.json() == {'id': login_session.id, 'user_id': login_session.user_id,
                'start': login_session.start.isoformat(), 'end': login_session.end.isoformat(),
                                    'stopped': login_session.stopped})

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.login_session_by_id',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1')
        assert response.status_code == 404
        assert response.json() == {'detail': [1]}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestLoginSessionAccessSessions:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, access_sessions):
        mocker.patch(
            'auth.db.query.login_session_access_sessions',
            return_value=access_sessions)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1/access_sessions')
        assert response.status_code == 200
        assert response.json() == [
            {
                'id': access_sessions[0].id,
                'login_session_id': access_sessions[0].login_session_id,
                'start': access_sessions[0].start.isoformat(),
                'end': access_sessions[0].end.isoformat(),
                'stopped': access_sessions[0].stopped
            },
            {
                'id': access_sessions[1].id,
                'login_session_id': access_sessions[1].login_session_id,
                'start': access_sessions[1].start.isoformat(),
                'end': access_sessions[1].end.isoformat(),
                'stopped': access_sessions[1].stopped
            }
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_empty(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.login_session_access_sessions',
            return_value=[])
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1/access_sessions')
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, authorization):
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1/access_sessions')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}
