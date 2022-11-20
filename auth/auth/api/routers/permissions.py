import fastapi as fs

import auth.api.schemas as sh

permissions_router = fs.APIRouter(prefix='/permissions')


@permissions_router.get('/{permission_name}')
async def permission_data(
    permission_name: str
) -> sh.Permission:  # type: ignore
    pass
