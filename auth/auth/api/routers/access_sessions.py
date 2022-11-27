from datetime import datetime

import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.security as sec

access_sessions_router = fs.APIRouter(
    prefix='/access_sessions', tags=['access_sessions'])


@access_sessions_router.post('/', response_model=sh.Token)
async def get_access_session(
    request: fs.Request,
    permissions: list[sh.PermissionName],
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Token:
    session_token = sh.SessionTokenData(jti=1, sub=1, exp=datetime.now())
    user_permissions = (await b.user_with_permissions(
        db_session,
        session_token.sub)).permissions
    requested_permissions_names = set(permissions)
    await b.check_requested_permissions(
        user_permissions,
        requested_permissions_names,
        request, db_session,
        session_token)
    requested_permissions = set(
        p for p in user_permissions if p.name in requested_permissions_names)
    expire_at = b.calculate_access_expiration(
        requested_permissions,
        session_token)
    await b.check_requested_services(
        requested_permissions,
        request, db_session,
        session_token)
    access_session = md.AccessSession(
        login_session_id=session_token.jti,
        start=datetime.utcnow(),
        end=expire_at)
    db_session.add(access_session)
    b.add_access_attempt(request, db_session, session_token)
    await db_session.commit()
    return sh.Token(
        token=sec.create_access_token(sh.AccessTokenData(
            jti=access_session.id,  # type: ignore
            sub=session_token.sub,
            pms=permissions,
            exp=expire_at).dict(),
            secret=bytes((await b.service_by_id(db_session, list(requested_permissions)[0].service_id)).key)),  # type: ignore
        type=sh.TokenType.ACCESS)


@access_sessions_router.get('/{id}', response_model=sh.AccessSession)
async def access_session_data(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> md.AccessSession:
    return await b.access_session_by_id(db_session, id)
