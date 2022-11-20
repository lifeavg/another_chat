import asyncio

import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.query as dq
import auth.security as sec

users_router = fs.APIRouter(prefix='/users')


@users_router.get('/{id}')
async def user_data(
    id: int,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.UserData:
    user = await b.user_by_id(db_session, id, True)
    return sh.UserData(id=user.id,  # type: ignore
                       external_id=user.external_id,  # type: ignore
                       login=user.login,  # type: ignore
                       confirmed=user.confirmed,  # type: ignore
                       created_timestamp=user.created_timestamp)  # type: ignore


@users_router.get('/{id}/permissions')
async def user_permissions(
    id: int,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[sh.PermissionName]:
    return await dq.user_permissions(db_session, id)


@users_router.post('/{id}/permissions/add')
async def add_user_permissions(
    id: int,
    permissions: list[sh.PermissionName],
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    perm_set: set[sh.PermissionName] = set(permissions)
    tasks = (asyncio.create_task(b.user_with_permissions_by_id(db_session, id)),
             asyncio.create_task(b.permissions_by_names(perm_set, db_session)))
    try:
        user, perms = await asyncio.gather(*tasks)
    except Exception as exception:
        for task in tasks:
            task.cancel()
        raise exception
    else:
        intersection = set(
            p.name for p in user.permissions).intersection(perm_set)
        if intersection:
            raise fs.HTTPException(
                status_code=fs.status.HTTP_409_CONFLICT,
                detail=list(intersection))
        user.permissions.append(*perms)
        await db_session.commit()


@users_router.post('/{id}/permissions/remove')
async def remove_user_permissions(
    id: int,
    permissions: list[sh.PermissionName],
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    perm_set: set[sh.PermissionName] = set(permissions)
    tasks = (b.user_with_permissions_by_id(db_session, id),
             b.permissions_by_names(perm_set, db_session))
    user, perms = await asyncio.gather(*tasks)
    intersection_diff = perm_set - \
        set(p.name for p in user.permissions).intersection(perm_set)
    if intersection_diff:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_409_CONFLICT,
            detail=list(intersection_diff))
    user.permissions.remove(*perms)
    await db_session.commit()


@users_router.get('/{id}/login_sessions')
async def user_login_sessions(
    id: int,
    active: bool | None = None,
    limit: int = 10,
    offset: int = 0,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[sh.LoginSession]:
    sessions = await dq.user_login_sessions(db_session, id, limit, offset, active)
    return [sh.LoginSession(
        id=s.id,  # type: ignore
        user_id=s.user_id,  # type: ignore
        start=s.start,  # type: ignore
        end=s.end,  # type: ignore
        stopped=s.stopped)  # type: ignore
        for s in sessions]


@users_router.put('/{id}')
async def update_user_state(
    id: int,
    confirmed: bool | None = None,
    active: bool | None = None,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    if confirmed is None and active is None:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_400_BAD_REQUEST,
            detail='Specify at least one parameter')
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


@users_router.post('/{id}/update')
async def update_user_data(
    login_data: sh.LoginData,
    id: int,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    user = await b.user_by_id(db_session, id)
    changed = False
    if login_data.login is not None:
        if user.login != login_data.login:
            await b.check_user_exists(login_data, db_session)
            user.login = login_data.login  # type: ignore
            changed = True
    if login_data.password is not None:
        b.validate_new_password(login_data)
        user.password = sec.password_hash(login_data.password)  # type: ignore
        changed = True
    if changed:
        await db_session.commit()


@users_router.delete('/{id}')
async def delete_user(
    id: int,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> int | None:
    deleted_id = await dq.delete_user(db_session, id)
    await db_session.commit()
    return deleted_id
