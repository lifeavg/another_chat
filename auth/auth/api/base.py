import functools
import fastapi  as fa
import asyncio

import auth.db.connection as con
import auth.db.query as dq
import auth.db.models as md
import auth.api.schemas as sh
import auth.security as sec


def canceled_task(function):
    # https://plainenglish.io/blog/how-to-manage-exceptions-when-waiting-on-multiple-asyncio
    @functools.wraps(function)
    async def wrapper(*args, **kwargs):
        try:
            return await function(*args, **kwargs)
        except asyncio.CancelledError:
            pass
    return wrapper


async def check_user_exists(
    data: sh.RegistrationData | sh.LoginData,
    db_session: con.AsyncSession
) -> None:
    if data.login is not None:
        existing_user = await dq.user_by_login(db_session, data.login)
        if existing_user:
            raise fa.HTTPException(
                status_code=fa.status.HTTP_409_CONFLICT,
                detail='Login already exists')

def validate_new_password(
    data: sh.RegistrationData | sh.LoginData
) -> None:
    if data.password is not None:
        valid, reason = sec.new_password_validator(data.password)
        if not valid:
            raise fa.HTTPException(
                status_code=fa.status.HTTP_409_CONFLICT,
                detail=reason)

async def create_new_user(
    registration_data: sh.RegistrationData,
    db_session: con.AsyncSession
) -> md.User:
    new_user = md.User(
        external_id=registration_data.external_id,
        login=registration_data.login,
        password=sec.password_hash(registration_data.password))
    db_session.add(new_user)
    await db_session.commit()
    return await dq.user_by_login(db_session, registration_data.login)

async def user_by_id(
    db_session: con.AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User:
    user = await dq.user_by_id(db_session, id, active)
    if not user:
        raise fa.HTTPException(
            status_code=fa.status.HTTP_404_NOT_FOUND,
            detail=f'No {"active " if active else ""}users with such id')
    return user

@canceled_task
async def user_with_permissions_by_id(
    db_session: con.AsyncSession,
    id: int,
    active: bool | None = None
) -> md.User:
    user = await dq.user_with_permissions(db_session, id, active)
    if not user:
        raise fa.HTTPException(
            status_code=fa.status.HTTP_404_NOT_FOUND,
            detail=f'No {"active " if active else ""}users with such id')
    return user

@canceled_task
async def permissions_by_names(
    permissions: set[sh.PermissionName],
    db_session: con.AsyncSession
) -> list[md.Permission]:
    perms = await dq.permissions_by_names(db_session, permissions)
    diff = permissions - set(p.name for p in perms)  # type: ignore
    if diff:
        raise fa.HTTPException(
            status_code=fa.status.HTTP_404_NOT_FOUND,
            detail=list(diff))
    return perms