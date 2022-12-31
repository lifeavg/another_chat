from datetime import datetime, timedelta, timezone

import pytest
from api_fixture import HOST, login, session
from db_response_fixture import login_sessions, user
from httpx import AsyncClient
from pytest_mock import mocker

import auth
from auth.api.routers.app import app
from auth.api.routers.exception import IntegrityError
from auth.api.schemas import LoginAttemptResult

BASE_URL: str = HOST


class TestSignup:
    @pytest.mark.asyncio
    async def test_ok(self, mocker, user, login):
        mocker.patch(
            'auth.api.base.create_new_user',
            return_value=user)
        mocker.patch(
            'auth.security.new_password_validator',
            return_value=(True, 'OK'))
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signup', json=login.dict())
        assert response.status_code == 201
        assert (response.json() ==
                {'id': user.id, 'login': user.login,
                 'confirmed': user.confirmed,
                 'created_timestamp': user.created_timestamp.isoformat()})

    @pytest.mark.asyncio
    async def test_exists(self, mocker, login):
        mocker.patch(
            'auth.api.base.commit_if_not_exists',
            side_effect=IntegrityError(f'DETAIL: {login.login}'))
        mocker.patch(
            'auth.security.new_password_validator',
            return_value=(True, 'OK'))
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signup', json=login.dict())
        assert response.status_code == 409
        assert (response.json() == {'detail': login.login})

    @pytest.mark.asyncio
    async def test_password_validation(self, mocker, user, login):
        mocker.patch(
            'auth.api.base.create_new_user',
            return_value=user)
        mocker.patch(
            'auth.security.new_password_validator',
            return_value=(False, 'REASON'))
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signup', json=login.dict())
        assert response.status_code == 409
        assert (response.json() == {'detail': 'REASON'})
        auth.api.base.create_new_user.assert_not_called()  # type: ignore


class TestSignin:
    @pytest.mark.asyncio
    async def test_ok(self, mocker, user, login):
        mocker.patch(
            'auth.db.query.user_by_login',
            return_value=user)
        mocker.patch(
            'auth.api.base.add_login_attempt')
        mocker.patch(
            'auth.api.base.add_login_session')
        mocker.patch(
            'auth.security.login_limit',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signin', json=login.dict())
        assert response.status_code == 200
        assert len(response.json()['token']) > 0
        assert response.json()['type'] == 'SESSION'
        auth.api.base.add_login_attempt.assert_called_once()  # type: ignore
        auth.api.base.add_login_session.assert_called_once()  # type: ignore
        assert (user in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or user in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore
        assert (LoginAttemptResult.SUCCESS in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or LoginAttemptResult.SUCCESS in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore
        assert (user in auth.api.base.add_login_session.call_args.args  # type: ignore
                or user in auth.api.base.add_login_session.call_args.kwargs.values())  # type: ignore

    @pytest.mark.asyncio
    async def test_limit_reached(self, mocker, login):
        mocker.patch(
            'auth.api.base.add_login_attempt')
        mocker.patch(
            'auth.api.base.add_login_session')
        mocker.patch(
            'auth.security.login_limit',
            return_value=timedelta(minutes=5))
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signin', json=login.dict())
        assert response.status_code == 429
        assert response.json() == {'detail': 'Login attempts limit reached'}
        auth.api.base.add_login_attempt.assert_called_once()  # type: ignore
        auth.api.base.add_login_session.assert_not_called()  # type: ignore
        assert (LoginAttemptResult.LIMIT_REACHED in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or LoginAttemptResult.LIMIT_REACHED in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore

    @pytest.mark.asyncio
    async def test_user_not_found(self, mocker, login):
        mocker.patch(
            'auth.db.query.user_by_login',
            return_value=None)
        mocker.patch(
            'auth.api.base.add_login_attempt')
        mocker.patch(
            'auth.api.base.add_login_session')
        mocker.patch(
            'auth.security.login_limit',
            return_value=None)
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signin', json=login.dict())
        assert response.status_code == 401
        assert response.json() == {'detail': 'Incorrect username or password'}
        auth.api.base.add_login_attempt.assert_called_once()  # type: ignore
        auth.api.base.add_login_session.assert_not_called()  # type: ignore
        assert (LoginAttemptResult.INCORRECT_LOGIN in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or LoginAttemptResult.INCORRECT_LOGIN in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore

    @pytest.mark.asyncio
    async def test_incorrect_password(self, mocker, user, login):
        mocker.patch(
            'auth.db.query.user_by_login',
            return_value=user)
        mocker.patch(
            'auth.api.base.add_login_attempt')
        mocker.patch(
            'auth.api.base.add_login_session')
        mocker.patch(
            'auth.security.login_limit',
            return_value=None)
        mocker.patch(
            'auth.security.verify_password',
            return_value=False)
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signin', json=login.dict())
        assert response.status_code == 401
        assert response.json() == {'detail': 'Incorrect username or password'}
        auth.api.base.add_login_attempt.assert_called_once()  # type: ignore
        auth.api.base.add_login_session.assert_not_called()  # type: ignore
        assert (user in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or user in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore
        assert (LoginAttemptResult.INCORRECT_PASSWORD in auth.api.base.add_login_attempt.call_args.args  # type: ignore
                or LoginAttemptResult.INCORRECT_PASSWORD in auth.api.base.add_login_attempt.call_args.kwargs.values())  # type: ignore


class TestSignout:
    @pytest.mark.asyncio
    async def test_ok(self, mocker, login_sessions, session):
        mocker.patch(
            'auth.db.query.user_login_sessions',
            return_value=login_sessions)
        async with AsyncClient(
                app=app, base_url=BASE_URL) as ac:
            response = await ac.post('/signout', headers=session)
        assert response.status_code == 200
        auth.db.query.user_login_sessions.assert_called_once()  # type: ignore
        assert login_sessions[0].stopped == True
        assert login_sessions[0].end < datetime.now(
            timezone.utc) + timedelta(minutes=1)
        assert login_sessions[0].end > datetime.now(
            timezone.utc) - timedelta(minutes=1)
        assert login_sessions[1].stopped == True
        assert login_sessions[1].end < datetime.now(
            timezone.utc) + timedelta(minutes=1)
        assert login_sessions[1].end > datetime.now(
            timezone.utc) - timedelta(minutes=1)
