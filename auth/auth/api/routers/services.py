import fastapi as fs
import auth.api.schemas as sh

services_router = fs.APIRouter(prefix='/services')

@services_router.get('/{service_name}')
async def service_data(
    name: str
) -> sh.Service:  # type: ignore
    pass


@services_router.post('/{service_name}/permissions')
async def add_service_permissions(
    name: str
) -> list[sh.PermissionName]:  # type: ignore
    pass


@services_router.get('/{service_name}/permissions')
async def service_permissions(
    name: str
) -> list[sh.PermissionName]:  # type: ignore
    pass


@services_router.delete('/{service_name}/permissions/{permission_name}')
async def delete_service_permission(
    service_name: str,
    permission_name: str
) -> None:
    pass


@services_router.put('/{service_name}')
async def update_service_key(
    service_name: str,
    key: str
) -> None:
    pass