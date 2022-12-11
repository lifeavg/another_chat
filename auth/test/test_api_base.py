from datetime import datetime, timezone, timedelta

import pytest
from pytest_mock import mocker

import auth
from auth.api.base import (check_requested_permissions, check_requested_services,
                           permissions_by_names, calculate_access_expiration)
from auth.api.routers.exception import DataNotFound, NoPermission, SingleServiceAllowed
from auth.api.schemas import AccessAttemptResult, SessionTokenData
from auth.db.models import Permission
from auth.db.query import AsyncSession


class Request:
    pass


@pytest.mark.asyncio
async def test_permissions_by_names_found(mocker):
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=[Permission(id=1, name='a', service_id=1),
                      Permission(id=2, name='b', service_id=1)])
    permissions = await permissions_by_names({'a', 'b'}, AsyncSession())
    assert len(permissions) == 2


@pytest.mark.asyncio
async def test_permissions_by_names_not_found(mocker):
    mocker.patch(
        'auth.db.query.permissions_by_names',
        return_value=[Permission(id=1, name='a', service_id=1),
                      Permission(id=2, name='b', service_id=1)])
    with pytest.raises(DataNotFound) as exception:
        await permissions_by_names({'a', 'b', 'c'}, AsyncSession())
        assert exception.value.args[0][0] == 'c'


@pytest.mark.asyncio
async def test_check_requested_permissions_allowed(mocker):
    mocker.patch(
        'auth.api.base.add_access_attempt',
        return_value=None)
    request = Request()
    db_session = AsyncSession()
    token = SessionTokenData(jti=1, sub=1, exp=datetime(3000, 12, 15, 1, 5, 3))
    result = await check_requested_permissions(
        [Permission(id=1, name='a', service_id=1),
         Permission(id=2, name='b', service_id=1)],
        {'a', 'b'}, request, db_session, token)  # type: ignore
    auth.api.base.add_access_attempt.assert_not_called()  # type: ignore
    assert result is None


@pytest.mark.asyncio
async def test_check_requested_permissions_not_allowed(mocker):
    mocker.patch(
        'auth.api.base.add_access_attempt',
        return_value=None)
    request = Request()
    db_session = AsyncSession()
    token = SessionTokenData(jti=1, sub=1, exp=datetime(3000, 12, 15, 1, 5, 3))
    with pytest.raises(NoPermission) as exception:
        await check_requested_permissions(
            [Permission(id=1, name='a', service_id=1),
             Permission(id=2, name='b', service_id=1)],
            {'a', 'b', 'c'}, request, db_session, token)  # type: ignore
        assert exception.value.args[0][0] == 'c'
    auth.api.base.add_access_attempt.assert_called_once_with(  # type: ignore
        request, db_session, token, AccessAttemptResult.PERMISSION_DENIED)
        


@pytest.mark.asyncio
async def test_check_requested_services_success(mocker):
    mocker.patch(
        'auth.api.base.add_access_attempt',
        return_value=None)
    request = Request()
    db_session = AsyncSession()
    token = SessionTokenData(jti=1, sub=1, exp=datetime(3000, 12, 15, 1, 5, 3))
    result = await check_requested_services(
        [Permission(id=1, name='a', service_id=1),
         Permission(id=2, name='b', service_id=1)],
        request, db_session, token)  # type: ignore
    auth.api.base.add_access_attempt.assert_not_called()  # type: ignore
    assert result is None


@pytest.mark.asyncio
async def test_check_requested_services_failed(mocker):
    mocker.patch(
        'auth.api.base.add_access_attempt',
        return_value=None)
    request = Request()
    db_session = AsyncSession()
    token = SessionTokenData(jti=1, sub=1, exp=datetime(3000, 12, 15, 1, 5, 3))
    with pytest.raises(SingleServiceAllowed):
        await check_requested_services(
            [Permission(id=1, name='a', service_id=1),
             Permission(id=2, name='b', service_id=2)],
            request, db_session, token)  # type: ignore
    auth.api.base.add_access_attempt.assert_called_once_with(  # type: ignore
        request, db_session, token, AccessAttemptResult.SINGLE_SERVICE)


def test_calculate_access_expiration():
    calculated_time = calculate_access_expiration(
        [Permission(id=1, name='a', service_id=1, expiration_min=10),
         Permission(id=2, name='b', service_id=2, expiration_min=20)],
        SessionTokenData(jti=1, sub=1, exp=datetime.now(timezone.utc) + timedelta(minutes=500)))
    assert calculated_time > datetime.now(timezone.utc) + timedelta(minutes=9)
    assert calculated_time < datetime.now(timezone.utc) + timedelta(minutes=11)
