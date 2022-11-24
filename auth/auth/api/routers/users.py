import asyncio

import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq
import auth.security as sec

users_router = fs.APIRouter(prefix='/users', tags=['user'])


@users_router.get('/{id}', response_model=sh.UserData)
async def user_data(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.UserData:
    return await b.user_by_id(db_session, id, True)


@users_router.get('/{id}/permissions', response_model=list[sh.PermissionName])
async def user_permissions(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[sh.PermissionName]:
    return await dq.user_permissions(db_session, id)


@users_router.post('/{id}/permissions/add', response_class=fs.Response)
async def add_user_permissions(
    permissions: list[sh.PermissionName],
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    perm_set: set[sh.PermissionName] = set(permissions)
    user, perms = await asyncio.gather(
        b.user_with_permissions_by_id(db_session, id),
        b.permissions_by_names(perm_set, db_session))
    intersection = set(
        p.name for p in user.permissions).intersection(perm_set)
    if intersection:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_409_CONFLICT,
            detail=list(intersection))
    user.permissions.append(*perms)
    await db_session.commit()


@users_router.post('/{id}/permissions/remove', response_class=fs.Response)
async def remove_user_permissions(
    permissions: list[sh.PermissionName],
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    perm_set: set[sh.PermissionName] = set(permissions)
    user, perms = await asyncio.gather(
        b.user_with_permissions_by_id(db_session, id),
        b.permissions_by_names(perm_set, db_session))
    intersection_diff = perm_set - \
        set(p.name for p in user.permissions).intersection(perm_set)
    if intersection_diff:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_409_CONFLICT,
            detail=list(intersection_diff))
    user.permissions.remove(*perms)
    await db_session.commit()


@users_router.get('/{id}/login_sessions', response_model=list[sh.LoginSession])
async def user_login_sessions(
    id: int = fs.Path(ge=0),
    active: bool | None = None,
    limit: int = fs.Query(default=10, gt=1, le=100),
    offset: int = fs.Query(default=0, ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[md.LoginSession]:
    return await dq.user_login_sessions(db_session, id, limit, offset, active)


@users_router.put('/{id}', response_class=fs.Response)
async def update_user_state(
    id: int = fs.Path(ge=0),
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


@users_router.post('/{id}/update', response_class=fs.Response)
async def update_user_data(
    login_data: sh.LoginData,
    id: int = fs.Path(ge=0),
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


@users_router.delete('/{id}', status_code=204)
async def delete_user(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    deleted_id = await dq.delete_user(db_session, id)
    if deleted_id is None:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_404_NOT_FOUND,
            detail=f'No user with such id')
    await db_session.commit()
