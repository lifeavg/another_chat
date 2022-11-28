import fastapi as fs

import auth.api.base as b
import auth.api.routers.exception as exc
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.query as dq
import auth.security as sec

permissions_router = fs.APIRouter(prefix='/permissions', tags=['permissions'])


@permissions_router.get('/{permission_name}', response_model=sh.Permission)
async def permission_data(
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_mod',), sh.AccessTokenData))
) -> sh.Permission:
    return await b.permission_by_name(db_session, permission_name)


@permissions_router.delete('/{permission_name}', status_code=fs.status.HTTP_204_NO_CONTENT)
async def delete_service_permission(
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_adm',), sh.AccessTokenData))
) -> None:
    deleted_permission = await dq.permission_delete(db_session, permission_name)
    if not deleted_permission:
        raise exc.DataNotFound([permission_name, ])
    await db_session.commit()


@permissions_router.put('/{permission_name}', response_class=fs.Response)
async def update_expiration_time(
    exp: int = fs.Query(ge=1),
    permission_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(('auth_mod',), sh.AccessTokenData))
) -> None:
    permission = await b.permission_by_name(db_session, permission_name)
    permission.expiration_min = exp   # type: ignore
    await db_session.commit()
