import fastapi as fs

import auth.api.schemas as sh
import auth.db.connection as con
import auth.api.base as b
import auth.db.query as dq

permissions_router = fs.APIRouter(prefix='/permissions', tags=['permissions'])


@permissions_router.get('/{permission_name}', response_model=sh.Permission)
async def permission_data(
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Permission:
    return await b.permission_by_name(db_session, permission_name)


@permissions_router.delete('/{permission_name}', status_code=204)
async def delete_service_permission(
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    deleted_permission = await dq.delete_permission(db_session, permission_name)
    if not deleted_permission:
        raise fs.HTTPException(
            status_code=fs.status.HTTP_404_NOT_FOUND,
            detail=f'No permissions with such name')
    await db_session.commit()


@permissions_router.put('/{permission_name}', response_class=fs.Response)
async def update_service_key(
    exp: int = fs.Query(ge=1),
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    permission = await b.permission_by_name(db_session, permission_name)
    permission.expiration_min = exp   # type: ignore
    await db_session.commit()