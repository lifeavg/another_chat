import fastapi as fs

import auth.api.schemas as sh
import auth.db.connection as con

permissions_router = fs.APIRouter(prefix='/permissions', tags=['permissions'])


@permissions_router.get('/{permission_name}')
async def permission_data(
    permission_name: str
) -> sh.Permission:  # type: ignore
    pass

@permissions_router.delete('/{permission_name}')
async def delete_service_permission(
    service_name: str,
    permission_name: str,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    pass