import fastapi as fs
import auth.db.connection as con
import auth.db.query as dq
import auth.api.schemas as sh
import auth.api.base as b
import asyncio


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
async def user_permissions_list(
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
        intersection = set(p.name for p in user.permissions).intersection(perm_set)
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
    tasks = (asyncio.create_task(b.user_with_permissions_by_id(db_session, id)),
             asyncio.create_task(b.permissions_by_names(perm_set, db_session)))
    try:
        user, perms = await asyncio.gather(*tasks)
    except Exception as exception:
        for task in tasks:
            task.cancel()
        raise exception
    else:
        intersection_diff = perm_set - set(p.name for p in user.permissions).intersection(perm_set)
        if intersection_diff:
            raise fs.HTTPException(
                status_code=fs.status.HTTP_409_CONFLICT,
                detail=list(intersection_diff))
        user.permissions.remove(*perms)
        await db_session.commit()


@users_router.get('/{id}/login_sessions')
async def user_login_sessions(
    id: int,
    active: bool | None = None
) -> list[sh.LoginSession]:  # type: ignore
    pass


@users_router.put('/{id}')
async def update_user_state(
        id: int,
        confirmed: bool | None = None,
        active: bool | None = None) -> None:
    pass


@users_router.post('/{id}/update')
async def update_user_data(login: sh.LoginData) -> None:
    pass


@users_router.delete('/{id}')
async def delete_user(id: int) -> None:
    pass