from datetime import datetime, timedelta, timezone

import pytest
from pytest_mock import mocker

from auth.api.schemas import SessionTokenData
from auth.db.models import LoginAttempt
from auth.db.query import AsyncSession
from auth.security import (create_token, login_limit, password_hash,
                           verify_password, verify_token)
from auth.settings import settings


def test_password_hash():
    password = 'qwerty1234_'
    assert verify_password(password, password_hash(password)) is True


def test_token():
    token = SessionTokenData(
        jti=1, sub=1,
        exp=datetime.now(timezone.utc).replace(microsecond=0))
    verified_token = verify_token(
        create_token(
            token.dict(), settings.security.session_key,
            settings.security.algorithm),
        SessionTokenData,
        settings.security.session_key, settings.security.algorithm)
    assert token == verified_token


@pytest.mark.asyncio
async def test_login_limit_not_reached(mocker):
    mocker.patch(
        'auth.db.query.login_attempt_by_fingerprint',
        return_value=[])
    assert (await login_limit(AsyncSession(), 'qwer', 30, 5)) is None


@pytest.mark.asyncio
async def test_login_limit_reached(mocker):
    mocker.patch(
        'auth.db.query.login_attempt_by_fingerprint',
        return_value=[LoginAttempt(date_time=datetime.now(timezone.utc)), LoginAttempt()])
    delay = await login_limit(AsyncSession(), 'qwer', 30, 1)
    assert delay is not None
    assert delay.seconds > timedelta(minutes=28).seconds
    assert delay.seconds < timedelta(minutes=32).seconds
