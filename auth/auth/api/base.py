from datetime import datetime, timedelta, timezone
from typing import Iterable

import fastapi as fa
from sqlalchemy.exc import IntegrityError as sqlIntegrityError

import auth.api.routers.exception as exc
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq
import auth.security as sec
from auth.settings import settings


async def commit_if_not_exists(db_session: con.AsyncSession) -> None:
    try:
        await db_session.commit()
    except sqlIntegrityError as exception:
        raise exc.IntegrityError(exception.args[0])


def validate_new_password(
    data: sh.Login
) -> None:
    valid, reason = sec.new_password_validator(data.password)
    if not valid:
        raise exc.NotSecureKey(reason)


async def create_new_user(
    registration_data: sh.Login,
    db_session: con.AsyncSession
) -> md.User:
    new_user = md.User(
        login=registration_data.login,
        password=sec.password_hash(registration_data.password),
        confirmed=False,
        active=True,
        created_timestamp=datetime.now(timezone.utc))
    db_session.add(new_user)
    await commit_if_not_exists(db_session)
    return new_user


async def user_by_id(
    db_session: con.AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User:
    user = await dq.user_by_id(db_session, id, active)
    if not user:
        raise exc.DataNotFound([id, ])
    return user


def add_login_attempt(
    request: fa.Request,
    db_session: con.AsyncSession,
    result: sh.LoginAttemptResult,
    user: md.User | None = None
) -> None:
    db_session.add(md.LoginAttempt(
        user_id=user.id if user is not None else None,
        fingerprint=request.client.host,  # type: ignore
        date_time=datetime.now(timezone.utc),
        response=result.value))


def add_access_attempt(
    request: fa.Request,
    db_session: con.AsyncSession,
    token: sh.SessionTokenData,
    result: sh.AccessAttemptResult
) -> None:
    db_session.add(md.AccessAttempt(
        login_session_id=token.jti,
        fingerprint=request.client.host,  # type: ignore
        date_time=datetime.now(timezone.utc),
        response=result.value))


async def check_login_limit(
    request: fa.Request,
    db_session: con.AsyncSession
) -> None:
    limit_delay = await sec.login_limit(
        db_session,
        request.client.host,  # type: ignore
        settings.security.attempt_delay,
        settings.security.max_attempt_count)
    if limit_delay:
        add_login_attempt(
            request, db_session,
            sh.LoginAttemptResult.LIMIT_REACHED)
        await db_session.commit()
        raise exc.LoginLimitReached()


async def check_login_data(
    login_data: sh.Login,
    user: md.User | None,
    db_session: con.AsyncSession,
    request: fa.Request
) -> None:
    if not user:
        add_login_attempt(
            request, db_session,
            sh.LoginAttemptResult.INCORRECT_LOGIN, user)
        await db_session.commit()
        raise exc.AuthorizationError()
    if not sec.verify_password(login_data.password, user.password):  # type: ignore
        add_login_attempt(request, db_session,
                          sh.LoginAttemptResult.INCORRECT_PASSWORD, user)
        await db_session.commit()
        raise exc.AuthorizationError()


def add_login_session(
    user: md.User,
    db_session: con.AsyncSession
) -> md.LoginSession:
    start = datetime.now(timezone.utc)
    expires = start + timedelta(minutes=settings.security.session_expire)
    session = md.LoginSession(
        user_id=user.id, start=start, end=expires)  # type: ignore
    db_session.add(session)
    return session


def add_access_session(
    token: sh.SessionTokenData,
    expire_at: datetime,
    db_session: con.AsyncSession
) -> md.AccessSession:
    access_session = md.AccessSession(
        login_session_id=token.jti,
        start=datetime.now(timezone.utc),
        end=expire_at)
    db_session.add(access_session)
    return access_session


def create_session_token(session: md.LoginSession) -> sh.Token:
    return sh.Token(
        token=sec.create_token(
            sh.SessionTokenData(
                jti=session.id,  # type: ignore
                sub=session.user_id,  # type: ignore
                exp=session.end).dict(), # type: ignore
            settings.security.session_key,
            settings.security.algorithm),
        type=sh.TokenType.SESSION)


async def user_with_permissions(
    db_session: con.AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User:
    user = await dq.user_with_permissions(db_session, id, active)
    if not user:
        raise exc.DataNotFound([id, ])
    return user


async def permissions_by_names(
    permissions: set[sh.PermissionName],
    db_session: con.AsyncSession
) -> list[md.Permission]:
    perms = await dq.permissions_by_names(db_session, permissions)
    diff = permissions - set(p.name for p in perms)  # type: ignore
    if diff:
        raise exc.DataNotFound(list(diff))
    return perms


async def service_by_name(
    db_session: con.AsyncSession,
    name: str,
) -> md.Service:
    service = await dq.service_by_name(db_session, name)
    if not service:
        raise exc.DataNotFound([name, ])
    return service


async def service_by_id(
    db_session: con.AsyncSession,
    id: int,
) -> md.Service:
    service = await dq.service_by_id(db_session, id)
    if not service:
        raise exc.DataNotFound([id, ])
    return service


def validate_new_key(
    key: str
) -> None:
    valid, reason = sec.new_key_validator(key)
    if not valid:
        raise exc.NotSecureKey(reason)


async def permission_by_name(
    db_session: con.AsyncSession,
    name: str,
) -> md.Permission:
    permission = await dq.permission_by_name(db_session, name)
    if not permission:
        raise exc.DataNotFound([name, ])
    return permission


async def login_session_by_id(
    db_session: con.AsyncSession,
    id: int
) -> md.LoginSession:
    login_session = await dq.login_session_by_id(db_session, id)
    if not login_session:
        raise exc.DataNotFound([id, ])
    return login_session


async def access_session_by_id(
    db_session: con.AsyncSession,
    id: int
) -> md.AccessSession:
    access_session = await dq.access_session_by_id(db_session, id)
    if not access_session:
        raise exc.DataNotFound([id, ])
    return access_session


async def check_requested_permissions(
    user_permissions: Iterable[md.Permission],
    requested_names: set[sh.PermissionName],
    request: fa.Request,
    db_session: con.AsyncSession,
    session_token: sh.SessionTokenData
) -> None:
    restricted = requested_names - \
        set(p.name for p in user_permissions)  # type: ignore
    if restricted:
        add_access_attempt(
            request,
            db_session,
            session_token,
            sh.AccessAttemptResult.PERMISSION_DENIED)
        await db_session.commit()
        raise exc.NoPermission(list(restricted))


async def check_requested_services(
    requested_permissions: Iterable[md.Permission],
    request: fa.Request,
    db_session: con.AsyncSession,
    session_token: sh.SessionTokenData
) -> None:
    services = set(p.service_id for p in requested_permissions)
    if len(services) > 1:
        add_access_attempt(
            request,
            db_session,
            session_token,
            sh.AccessAttemptResult.SINGLE_SERVICE)
        await db_session.commit()
        raise exc.SingleServiceAllowed()


def calculate_access_expiration(
    requested_permissions: Iterable[md.Permission],
    session_token: sh.SessionTokenData
) -> datetime:
    permission_min_time = min(
        requested_permissions,
        key=lambda x: x.expiration_min)  # type: ignore
    min_time = min(
        divmod((session_token.exp - datetime.now(timezone.utc)
                ).total_seconds(), 60)[0],
        permission_min_time.expiration_min)
    return datetime.now(timezone.utc) + timedelta(minutes=min_time)
