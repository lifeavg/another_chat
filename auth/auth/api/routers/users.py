import asyncio

import fastapi as fs

import auth.api.base as b
import auth.api.routers.exception as exc
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq
import auth.security as sec

users_router = fs.APIRouter(prefix='/users', tags=['user'])


@users_router.get('/{id}', response_model=sh.User)
async def user_data(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_inf_user',), sh.AccessTokenData))
) -> sh.User:
    return await b.user_by_id(db_session, id, True)


@users_router.get('/{id}/permissions', response_model=list[sh.PermissionName])
async def user_permissions(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> list[sh.PermissionName]:
    return [perm.name for perm in (await b.user_with_permissions(db_session, id)).permissions]


@users_router.post('/{id}/permissions/add', response_class=fs.Response)
async def add_user_permissions(
    permissions: list[sh.PermissionName],
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> None:
    task_result = await asyncio.gather(
        b.user_with_permissions(db_session, id),
        b.permissions_by_names(set(permissions), db_session),
        return_exceptions=True)
    exceptions = [e for e in task_result if isinstance(e, Exception)]
    if exceptions:
        raise exceptions[0]
    user, permissions_db = task_result
    new_permissions = set(permissions_db) - set(user.permissions) # type: ignore
    if new_permissions:
        user.permissions.append(*new_permissions)  # type: ignore
        await db_session.commit()


@users_router.post('/{id}/permissions/remove', response_class=fs.Response)
async def remove_user_permissions(
    permissions: list[sh.PermissionName],
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> None:
    task_result = await asyncio.gather(
        b.user_with_permissions(db_session, id),
        b.permissions_by_names(set(permissions), db_session))
    exceptions = [e for e in task_result if isinstance(e, Exception)]
    if exceptions:
        raise exceptions[0]
    user, permissions_db = task_result
    existing_permissions = set(permissions_db).intersection(user.permissions)
    if existing_permissions:
        user.permissions.remove(*existing_permissions)
        await db_session.commit()


@users_router.get('/{id}/login_sessions', response_model=list[sh.LoginSession])
async def user_login_sessions(
    id: int = fs.Path(ge=0),
    active: bool | None = None,
    limit: int = fs.Query(default=10, ge=1, le=100),
    offset: int = fs.Query(default=0, ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> list[md.LoginSession]:
    return await dq.user_login_sessions(db_session, id, limit, offset, active)


@users_router.put('/{id}', response_class=fs.Response)
async def update_user_state(
    id: int = fs.Path(ge=0),
    confirmed: bool | None = None,
    active: bool | None = None,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> None:
    if confirmed is None and active is None:
        raise exc.ParameterRequeued()
    user = await b.user_by_id(db_session, id)
    changed = False
    if confirmed is not None:
        user.confirmed = confirmed  # type: ignore
        changed = True
    if active is not None:
        user.active = active  # type: ignore
        changed = True
    if changed:
        await db_session.commit()


@users_router.post('/{id}/update', response_class=fs.Response)
async def update_user_data(
    login_data: sh.Login,
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_upd_user',), sh.AccessTokenData))
) -> None:
    user = await b.user_by_id(db_session, id)
    changed = False
    if user.login != login_data.login:
        user.login = login_data.login  # type: ignore
        changed = True
    b.validate_new_password(login_data)
    user.password = sec.password_hash(login_data.password)  # type: ignore
    changed = True
    if changed:
        await b.commit_if_not_exists(db_session)


@users_router.delete('/{id}', status_code=fs.status.HTTP_204_NO_CONTENT)
async def delete_user(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_del_user',), sh.AccessTokenData))
) -> None:
    deleted_id = await dq.user_delete(db_session, id)
    if deleted_id is None:
        raise exc.DataNotFound([id, ])
    await db_session.commit()
