import fastapi as fs

import auth.api.base as b
import auth.api.routers.exception as exc
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq

services_router = fs.APIRouter(prefix='/services', tags=['services'])


@services_router.post('/', status_code=fs.status.HTTP_201_CREATED, response_class=fs.Response)
async def create_service(
    new_service: sh.Service,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    b.validate_new_key(new_service.key)
    db_session.add(md.Service(name=new_service.name, key=new_service.key))
    await b.commit_if_not_exists(db_session)


@services_router.get('/{service_name}', response_model=sh.Service)
async def service_data(
    service_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Service:
    return await b.service_by_name(db_session, service_name)


@services_router.post('/{service_name}/permissions', response_class=fs.Response)
async def add_service_permissions(
    new_permission: sh.Permission,
    service_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    service = await b.service_by_name(db_session, service_name)
    db_session.add(md.Permission(
        name=new_permission.name,
        service_id=service.id,
        expiration_min=new_permission.expiration_min))
    await b.commit_if_not_exists(db_session)


@services_router.get('/{service_name}/permissions', response_model=list[sh.Permission])
async def service_permissions(
    service_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> list[md.Permission]:
    return await dq.service_permissions(db_session, service_name)


@services_router.put('/{service_name}', response_class=fs.Response)
async def update_service_key(
    key: sh.Key,
    service_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    service = await b.service_by_name(db_session, service_name)
    b.validate_new_key(key.key)
    service.key = key.key  # type: ignore
    await db_session.commit()


@services_router.delete('/{service_name}', status_code=fs.status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_name: str = fs.Path(max_length=128),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    deleted_service = await dq.service_delete(db_session, service_name)
    if not deleted_service:
        raise exc.DataNotFound([service_name, ])
    await db_session.commit()
