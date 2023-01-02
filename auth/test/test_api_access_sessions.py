import pytest
from api_fixture import HOST, authorization, session
from db_response_fixture import access_session, service, user_with_permissions
from httpx import AsyncClient
from pytest_mock import mocker

import auth
from auth.api.schemas import AccessAttemptResult
from auth.main import app

BASE_URL: str = HOST + '/access_sessions'


class TestAccessSessionData:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_ok(self, mocker, authorization, access_session):
        mocker.patch(
            'auth.db.query.access_session_by_id',
            return_value=access_session)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get(f'/{access_session.id}')
        assert response.status_code == 200
        assert (response.json() == {
            'id': access_session.id,
            'login_session_id': access_session.login_session_id,
            'start': access_session.start.isoformat(),
            'end': access_session.end.isoformat(),
            'stopped': access_session.stopped})

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth_adm'],])
    async def test_not_found(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.access_session_by_id',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1')
        assert response.status_code == 404
        assert response.json() == {'detail': [1]}

    @pytest.mark.asyncio
    @pytest.mark.parametrize('perms', [['auth'],])
    async def test_no_permission(self, mocker, authorization):
        mocker.patch(
            'auth.db.query.access_session_by_id',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=authorization) as ac:
            response = await ac.get('/1')
        assert response.status_code == 403
        assert response.json() == {
            'detail': 'Invalid authorization code: type'}


class TestGetAccessSession:
    @pytest.mark.asyncio
    async def test_ok(self, mocker, session, user_with_permissions, service, access_session):
        mocker.patch(
            'auth.db.query.user_with_permissions',
            return_value=user_with_permissions)
        mocker.patch('auth.api.base.add_access_attempt')
        mocker.patch(
            'auth.api.base.add_access_session',
            return_value=access_session)
        # calculate_access_expiration
        # check_requested_services
        mocker.patch(
            'auth.db.query.service_by_id',
            return_value=service)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=session) as ac:
            response = await ac.post('/',
                                     json=[user_with_permissions.permissions[0].name,
                                           user_with_permissions.permissions[1].name])
        assert response.status_code == 200
        assert len(response.json()['token']) > 0
        assert response.json()['type'] == 'ACCESS'
        assert (AccessAttemptResult.SUCCESS in auth.api.base.add_access_attempt.call_args.args  # type: ignore
                or AccessAttemptResult.SUCCESS in auth.api.base.add_access_attempt.call_args.kwargs.values())  # type: ignore
        auth.api.base.add_access_session.assert_called_once()  # type: ignore

    @pytest.mark.asyncio
    async def test_user_not_found(self, mocker, session, user_with_permissions, service, access_session):
        mocker.patch(
            'auth.db.query.user_with_permissions',
            return_value=None)
        mocker.patch('auth.api.base.add_access_attempt')
        mocker.patch(
            'auth.api.base.add_access_session',
            return_value=access_session)
        mocker.patch(
            'auth.db.query.service_by_id',
            return_value=service)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=session) as ac:
            response = await ac.post('/',
                                     json=[user_with_permissions.permissions[0].name,
                                           user_with_permissions.permissions[1].name])
        assert response.status_code == 404
        assert response.json() == {'detail': [1]}
        auth.api.base.add_access_session.assert_not_called()  # type: ignore

    @pytest.mark.asyncio
    async def test_permission_denied(self, mocker, session, user_with_permissions, service, access_session):
        mocker.patch(
            'auth.db.query.user_with_permissions',
            return_value=user_with_permissions)
        mocker.patch('auth.api.base.add_access_attempt')
        mocker.patch(
            'auth.api.base.add_access_session',
            return_value=access_session)
        mocker.patch(
            'auth.db.query.service_by_id',
            return_value=service)
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=session) as ac:
            response = await ac.post('/',
                                     json=[user_with_permissions.permissions[0].name,
                                           user_with_permissions.permissions[1].name,
                                           'p91'])
        assert response.status_code == 403
        assert response.json() == {'detail': ['p91']}
        assert (AccessAttemptResult.PERMISSION_DENIED in auth.api.base.add_access_attempt.call_args.args  # type: ignore
                or AccessAttemptResult.PERMISSION_DENIED in auth.api.base.add_access_attempt.call_args.kwargs.values())  # type: ignore
        auth.api.base.add_access_session.assert_not_called()  # type: ignore

    @pytest.mark.asyncio
    async def test_single_service(self, mocker, session, user_with_permissions, service, access_session):
        mocker.patch(
            'auth.db.query.user_with_permissions',
            return_value=user_with_permissions)
        mocker.patch('auth.api.base.add_access_attempt')
        mocker.patch(
            'auth.api.base.add_access_session',
            return_value=access_session)
        mocker.patch(
            'auth.db.query.service_by_id',
            return_value=service)
        user_with_permissions.permissions[1].service_id = user_with_permissions.permissions[1].service_id + 1
        async with AsyncClient(
                app=app, base_url=BASE_URL, headers=session) as ac:
            response = await ac.post('/',
                                     json=[user_with_permissions.permissions[0].name,
                                           user_with_permissions.permissions[1].name])
        assert response.status_code == 400
        assert response.json() == {
            'detail': 'Token issued only for single service'}
        assert (AccessAttemptResult.SINGLE_SERVICE in auth.api.base.add_access_attempt.call_args.args  # type: ignore
                or AccessAttemptResult.SINGLE_SERVICE in auth.api.base.add_access_attempt.call_args.kwargs.values())  # type: ignore
        auth.api.base.add_access_session.assert_not_called()  # type: ignore
