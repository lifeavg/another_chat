from datetime import datetime, timedelta, timezone

import pytest
from models_fixtures import (active_login_session, active_user, engine,
                             event_loop, inactive_access_session_expired,
                             inactive_access_session_stopped,
                             inactive_login_session_expired,
                             inactive_login_session_stopped, inactive_user,
                             service, service_permission, session,
                             successful_login_attempt,
                             unsuccessful_login_attempt, user_permission,
                             unsuccessful_login_attempt_expired,
                             active_access_session,
                             successful_access_attempt)

from auth.db.query import (login_session_access_sessions, login_session_by_id,
                           permission_by_name, service_by_id, service_by_name,
                           service_permissions, user_by_id, user_by_login,
                           user_login_sessions, user_with_permissions,
                           access_session_by_id, permissions_by_names,
                           login_attempt_by_fingerprint)


class TestUserByLogin:
    @pytest.mark.asyncio
    async def test_active_found(self, session, active_user):
        user = await user_by_login(session, active_user.login, True)
        assert active_user.id == user.id  # type: ignore

    @pytest.mark.asyncio
    async def test_active_not_found(self, session, inactive_user):
        user = await user_by_login(session, inactive_user.login, True)
        assert user is None

    @pytest.mark.asyncio
    async def test_inactive_found(self, session, inactive_user):
        user = await user_by_login(session, inactive_user.login, False)
        assert inactive_user.id == user.id  # type: ignore

    @pytest.mark.asyncio
    async def test_inactive_not_found(self, session, active_user):
        user = await user_by_login(session, active_user.login, False)
        assert user is None


class TestUserById:
    @pytest.mark.asyncio
    async def test_active_found(self, session, active_user):
        user = await user_by_id(session, active_user.id, True)
        assert active_user.login == user.login  # type: ignore

    @pytest.mark.asyncio
    async def test_active_not_found(self, session, inactive_user):
        user = await user_by_id(session, inactive_user.id, True)
        assert user is None

    @pytest.mark.asyncio
    async def test_inactive_found(self, session, inactive_user):
        user = await user_by_id(session, inactive_user.id, False)
        assert inactive_user.login == user.login  # type: ignore

    @pytest.mark.asyncio
    async def test_inactive_not_found(self, session, active_user):
        user = await user_by_id(session, active_user.id, False)
        assert user is None


class TestUserWithPermissions:
    @pytest.mark.asyncio
    async def test_active_found_with_permissions(self, session, user_permission):
        user = await user_with_permissions(session, user_permission[0].id, True)
        assert user_permission[0].login == user.login  # type: ignore
        assert len(user.permissions) == 1  # type: ignore
        assert (user_permission[1].name
                == user.permissions[0].name)  # type: ignore

    @pytest.mark.asyncio
    async def test_active_found_no_permissions(self, session, active_user):
        user = await user_with_permissions(session, active_user.id, True)
        assert active_user.login == user.login  # type: ignore
        assert len(active_user.permissions) == 0

    @pytest.mark.asyncio
    async def test_active_not_found(self, session, inactive_user):
        user = await user_with_permissions(session, inactive_user.id, True)
        assert user is None

    @pytest.mark.asyncio
    async def test_inactive_found(self, session, inactive_user):
        user = await user_with_permissions(session, inactive_user.id, False)
        assert inactive_user.login == user.login  # type: ignore

    @pytest.mark.asyncio
    async def test_inactive_not_found(self, session, active_user):
        user = await user_with_permissions(session, active_user.id, False)
        assert user is None


class TestUserLoginSessions:
    @pytest.mark.asyncio
    async def test_active(self, session, active_login_session):
        login_sessions = await user_login_sessions(
            session, active_login_session.user_id, 10, 0, True)
        assert len(login_sessions) == 1
        assert login_sessions[0].id == active_login_session.id

    @pytest.mark.asyncio
    async def test_stopped(self, session, inactive_login_session_stopped):
        login_sessions = await user_login_sessions(
            session, inactive_login_session_stopped.user_id, 10, 0, False)
        assert len(login_sessions) == 1
        assert login_sessions[0].id == inactive_login_session_stopped.id

    @pytest.mark.asyncio
    async def test_expired(self, session, inactive_login_session_expired):
        login_sessions = await user_login_sessions(
            session, inactive_login_session_expired.user_id, 10, 0, False)
        assert len(login_sessions) == 1
        assert login_sessions[0].id == inactive_login_session_expired.id


@pytest.mark.skip(reason='to do')
class TestUserDelete:
    pass


class TestServiceByName:
    @pytest.mark.asyncio
    async def test_found(self, session, service):
        db_service = await service_by_name(session, service.name)
        assert service.id == db_service.id  # type: ignore

    @pytest.mark.asyncio
    async def test_not_found(self, session, service):
        db_service = await service_by_name(session, 'aaa')
        assert db_service is None


class TestServiceById:
    @pytest.mark.asyncio
    async def test_found(self, session, service):
        db_service = await service_by_id(session, service.id)
        assert service.name == db_service.name  # type: ignore

    @pytest.mark.asyncio
    async def test_not_found(self, session, service):
        db_service = await service_by_id(session, 99999999)
        assert db_service is None


class TestServicePermissions:
    @pytest.mark.asyncio
    async def test_not_empty(self, session, service_permission):
        permissions = await service_permissions(session, service_permission[1].name)
        assert len(permissions) == 1
        assert permissions[0].id == service_permission[0].id

    @pytest.mark.asyncio
    async def test_empty(self, session, service):
        permissions = await service_permissions(session, service.name)
        assert len(permissions) == 0


@pytest.mark.skip(reason='to do')
class TestServiceDelete:
    pass


class TestPermissionByName:
    @pytest.mark.asyncio
    async def test_found(self, session, service_permission):
        permission = await permission_by_name(session, service_permission[0].name)
        assert service_permission[0].id == permission.id  # type: ignore

    @pytest.mark.asyncio
    async def test_not_found(self, session, service_permission):
        permission = await permission_by_name(session, 'aaa')
        assert permission is None


@pytest.mark.skip(reason='to do')
class TestPermissionDelete:
    pass


class TestLoginSessionById:
    @pytest.mark.asyncio
    async def test_active_found(self, session, active_login_session):
        login_session = await login_session_by_id(session, active_login_session.id)
        assert login_session.id == active_login_session.id  # type: ignore

    @pytest.mark.asyncio
    async def test_active_not_found(self, session, active_login_session):
        login_session = await login_session_by_id(session, 99999)
        assert login_session is None

    @pytest.mark.asyncio
    async def test_inactive_found(self, session, inactive_login_session_stopped):
        login_session = await login_session_by_id(session, inactive_login_session_stopped.id)
        assert login_session.id == inactive_login_session_stopped.id  # type: ignore


class TestLoginSessionAccessSessions:
    @pytest.mark.asyncio
    async def test_active(self, session, active_access_session):
        access_sessions = await login_session_access_sessions(
            session, active_access_session.login_session_id, True)
        assert len(access_sessions) == 1
        assert access_sessions[0].id == active_access_session.id

    @pytest.mark.asyncio
    async def test_stopped(self, session, inactive_access_session_stopped):
        access_sessions = await login_session_access_sessions(
            session, inactive_access_session_stopped.login_session_id, False)
        assert len(access_sessions) == 1
        assert access_sessions[0].id == inactive_access_session_stopped.id

    @pytest.mark.asyncio
    async def test_expired(self, session, inactive_access_session_expired):
        access_sessions = await login_session_access_sessions(
            session, inactive_access_session_expired.login_session_id, False)
        assert len(access_sessions) == 1
        assert access_sessions[0].id == inactive_access_session_expired.id


class TestAccessSessionById:
    @pytest.mark.asyncio
    async def test_found(self, session, active_access_session):
        access_session = await access_session_by_id(session, active_access_session.id)
        assert active_access_session.id == access_session.id  # type: ignore

    @pytest.mark.asyncio
    async def test_not_found(self, session, active_access_session):
        access_session = await access_session_by_id(session, 9999999)
        assert access_session is None


class TestPermissionsByNames:
    @pytest.mark.asyncio
    async def test_found(self, session, service_permission):
        permissions = await permissions_by_names(
            session, [service_permission[0].name, service_permission[0].name])
        assert len(permissions) == 1
        assert permissions[0].id == service_permission[0].id

    @pytest.mark.asyncio
    async def test_not_found(self, session, service_permission):
        permissions = await permissions_by_names(session, ['aaa', 'aaa', 'bbb'])
        assert len(permissions) == 0


class TestLoginAttemptByFingerprint:
    @pytest.mark.asyncio
    async def test_fingerprint_not_found(self, session, successful_login_attempt):
        login_attempts = await login_attempt_by_fingerprint(session, 'aaa', 30)
        assert len(login_attempts) == 0

    @pytest.mark.asyncio
    async def test_response_in_allowed(self, session, successful_login_attempt):
        login_attempts = await login_attempt_by_fingerprint(
            session, successful_login_attempt[0].fingerprint, 30)
        assert len(login_attempts) == 0

    @pytest.mark.asyncio
    async def test_delay_passed(self, session, unsuccessful_login_attempt_expired):
        login_attempts = await login_attempt_by_fingerprint(
            session, unsuccessful_login_attempt_expired[0].fingerprint, 30)
        assert len(login_attempts) == 0

    @pytest.mark.asyncio
    async def test_found(self, session, unsuccessful_login_attempt):
        login_attempts = await login_attempt_by_fingerprint(
            session, unsuccessful_login_attempt[0].fingerprint, 30)
        assert len(login_attempts) == 1
        assert login_attempts[0].id == unsuccessful_login_attempt[0].id