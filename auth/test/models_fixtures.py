import asyncio
import random
import string
from datetime import datetime, timedelta, timezone
from random import randint

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from auth.api.schemas import AccessAttemptResult, LoginAttemptResult
from auth.db.models import (AccessAttempt, AccessSession, LoginAttempt,
                            LoginSession, Permission, Service, User)
from auth.security import password_hash

TEARDOWN: bool = True


def random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


@pytest.fixture(scope='session')
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope='session')
def engine():
    DB_CONNECTION = 'postgresql+asyncpg'
    DB_USER = 'postgres'
    DB_PASSWORD = 'mysecretpassword'
    DB_HOST = 'localhost:5432'
    DB_NAME = 'test'
    return create_async_engine(
        f'{DB_CONNECTION}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}',
        echo=True)


@pytest_asyncio.fixture
async def session(engine):
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False)
    async with async_session() as session:  # type: ignore
        yield session


@pytest_asyncio.fixture
async def active_user(session):
    user = User(
        login=random_string(10),
        password=password_hash(random_string(10)),
        confirmed=True,
        active=True)
    session.add(user)
    await session.commit()
    user = (await session.execute(select(User)
                                  .where(User.id == user.id))
            ).scalars().one()
    yield user
    if TEARDOWN:
        await session.execute(delete(User)
                              .where(User.id == user.id))
        await session.commit()


@pytest_asyncio.fixture
async def inactive_user(session):
    user = User(
        login=random_string(10),
        password=password_hash(random_string(10)),
        confirmed=True,
        active=False)
    session.add(user)
    await session.commit()
    user = (await session.execute(select(User)
                                  .where(User.id == user.id))
            ).scalars().one()
    await session.close()
    yield user
    if TEARDOWN:
        await session.execute(delete(User)
                              .where(User.id == user.id))
        await session.commit()


@pytest_asyncio.fixture
async def service(session):
    service = Service(
        name=random_string(10),
        key=random_string(10))
    session.add(service)
    await session.commit()
    yield service
    if TEARDOWN:
        await session.execute(delete(Service)
                              .where(Service.id == service.id))
        await session.commit()


@pytest_asyncio.fixture
async def service_permission(session, service):
    permission = Permission(
        name=random_string(10),
        service_id=service.id,
        expiration_min=randint(5, 10))
    session.add(permission)
    await session.commit()
    yield permission, service
    if TEARDOWN:
        await session.execute(delete(Permission)
                              .where(Permission.id == permission.id))
        await session.commit()


@pytest_asyncio.fixture
async def user_permission(session, service_permission, active_user):
    user = (await session.execute(select(User)
                                  .where(User.id == active_user.id)
                                  .options(selectinload(User.permissions)))
            ).scalars().one()
    user.permissions.append(service_permission[0])
    await session.commit()
    yield user, service_permission[0]
    if TEARDOWN:
        user.permissions.remove(service_permission[0])
        await session.commit()


@pytest_asyncio.fixture
async def successful_login_attempt(session, user_permission):
    login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=random_string(10),
        date_time=datetime.now(timezone.utc),
        response=LoginAttemptResult.SUCCESS.value)
    session.add(login_attempt)
    await session.commit()
    yield login_attempt, user_permission
    if TEARDOWN:
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == login_attempt.id))
        await session.commit()


@pytest_asyncio.fixture
async def unsuccessful_login_attempt(session, user_permission):
    fingerprint = random_string(10)
    login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc),
        response=LoginAttemptResult.INCORRECT_PASSWORD.value)
    successful_login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc),
        response=LoginAttemptResult.SUCCESS.value)
    expired_login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc) - timedelta(minutes=60),
        response=LoginAttemptResult.INCORRECT_PASSWORD.value)
    session.add(login_attempt)
    session.add(successful_login_attempt)
    session.add(expired_login_attempt)
    await session.commit()
    yield login_attempt, user_permission
    if TEARDOWN:
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == login_attempt.id))
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == successful_login_attempt.id))
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == expired_login_attempt.id))
        await session.commit()


@pytest_asyncio.fixture
async def unsuccessful_login_attempt_expired(session, user_permission):
    fingerprint = random_string(10)
    login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc) - timedelta(minutes=60),
        response=LoginAttemptResult.INCORRECT_PASSWORD.value)
    unsuccessful_login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc),
        response=LoginAttemptResult.LIMIT_REACHED.value)
    successful_login_attempt = LoginAttempt(
        user_id=user_permission[0].id,
        fingerprint=fingerprint,
        date_time=datetime.now(timezone.utc),
        response=LoginAttemptResult.SUCCESS.value)
    session.add(login_attempt)
    session.add(unsuccessful_login_attempt)
    session.add(successful_login_attempt)
    await session.commit()
    yield login_attempt, user_permission
    if TEARDOWN:
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == login_attempt.id))
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == unsuccessful_login_attempt.id))
        await session.execute(delete(LoginAttempt)
                              .where(LoginAttempt.id == successful_login_attempt.id))
        await session.commit()


@pytest_asyncio.fixture
async def active_login_session(session, successful_login_attempt):
    login_session = LoginSession(
        user_id=successful_login_attempt[0].user_id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=60),
        stopped=False)
    stopped_login_session = LoginSession(
        user_id=successful_login_attempt[0].user_id,
        start=datetime.now(timezone.utc) - timedelta(minutes=20),
        end=datetime.now(timezone.utc) + timedelta(minutes=20),
        stopped=True)
    expired_login_session = LoginSession(
        user_id=successful_login_attempt[0].user_id,
        start=datetime.now(timezone.utc) - timedelta(minutes=120),
        end=datetime.now(timezone.utc) - timedelta(minutes=20),
        stopped=False)
    session.add(login_session)
    session.add(stopped_login_session)
    session.add(expired_login_session)
    await session.commit()
    yield login_session
    if TEARDOWN:
        await session.execute(delete(LoginSession)
                              .where(LoginSession.id == login_session.id))
        await session.execute(delete(LoginSession)
                              .where(LoginSession.id == stopped_login_session.id))
        await session.execute(delete(LoginSession)
                              .where(LoginSession.id == expired_login_session.id))
        await session.commit()


@pytest_asyncio.fixture
async def inactive_login_session_stopped(session, unsuccessful_login_attempt):
    login_session = LoginSession(
        user_id=unsuccessful_login_attempt[0].user_id,
        start=datetime.now(timezone.utc) - timedelta(minutes=20),
        end=datetime.now(timezone.utc) + timedelta(minutes=20),
        stopped=True)
    session.add(login_session)
    await session.commit()
    yield login_session
    if TEARDOWN:
        await session.execute(delete(LoginSession)
                              .where(LoginSession.id == login_session.id))
        await session.commit()


@pytest_asyncio.fixture
async def inactive_login_session_expired(session, unsuccessful_login_attempt):
    login_session = LoginSession(
        user_id=unsuccessful_login_attempt[0].user_id,
        start=datetime.now(timezone.utc) - timedelta(minutes=120),
        end=datetime.now(timezone.utc) - timedelta(minutes=20),
        stopped=False)
    session.add(login_session)
    await session.commit()
    yield login_session
    if TEARDOWN:
        await session.execute(delete(LoginSession)
                              .where(LoginSession.id == login_session.id))
        await session.commit()


@pytest_asyncio.fixture
async def successful_access_attempt(session, active_login_session):
    access_attempt = AccessAttempt(
        login_session_id=active_login_session.id,
        fingerprint=random_string(10),
        date_time=datetime.now(timezone.utc),
        response=AccessAttemptResult.SUCCESS.value)
    session.add(access_attempt)
    await session.commit()
    yield access_attempt, active_login_session
    if TEARDOWN:
        await session.execute(delete(AccessAttempt)
                              .where(AccessAttempt.id == access_attempt.id))
        await session.commit()


@pytest_asyncio.fixture
async def active_access_session(session, successful_access_attempt):
    access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=30),
        stopped=False)
    expired_access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc) - timedelta(minutes=40),
        end=datetime.now(timezone.utc) - timedelta(minutes=10),
        stopped=False)
    stopped_access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=30),
        stopped=True)
    session.add(access_session)
    session.add(expired_access_session)
    session.add(stopped_access_session)
    await session.commit()
    yield access_session
    if TEARDOWN:
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == access_session.id))
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == expired_access_session.id))
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == stopped_access_session.id))
        await session.commit()


@pytest_asyncio.fixture
async def inactive_access_session_stopped(session, successful_access_attempt):
    access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=30),
        stopped=True)
    running_access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=30),
        stopped=False)
    session.add(access_session)
    session.add(running_access_session)
    await session.commit()
    yield access_session
    if TEARDOWN:
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == access_session.id))
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == running_access_session.id))
        await session.commit()


@pytest_asyncio.fixture
async def inactive_access_session_expired(session, successful_access_attempt):
    access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc) - timedelta(minutes=40),
        end=datetime.now(timezone.utc) - timedelta(minutes=10),
        stopped=False)
    running_access_session = AccessSession(
        login_session_id=successful_access_attempt[1].id,
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(minutes=30),
        stopped=False)
    session.add(access_session)
    session.add(running_access_session)
    await session.commit()
    yield access_session
    if TEARDOWN:
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == access_session.id))
        await session.execute(delete(AccessSession)
                              .where(AccessSession.id == running_access_session.id))
        await session.commit()
