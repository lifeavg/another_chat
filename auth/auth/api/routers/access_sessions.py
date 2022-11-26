import fastapi as fs
from datetime import datetime, timedelta

import auth.api.schemas as sh
import auth.db.connection as con
import auth.api.base as b
import auth.db.query as dq
import auth.db.models as md
import auth.security as sec

access_sessions_router = fs.APIRouter(prefix='/access_sessions', tags=['access_sessions'])


@access_sessions_router.post('/', response_model=sh.Token)
async def get_access_session(
    request: fs.Request,
    permissions: list[sh.PermissionName],
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Token:
    session_token = sh.SessionTokenData(jti=1, sub=1, exp = datetime.now())
    login_session_id = 1
    user_permissions = await dq.user_permissions(db_session, session_token.sub)
    requested_permissions_names = set(permissions)
    user_permissions_names = set(p.name for p in user_permissions)
    diff = requested_permissions_names - user_permissions_names
    if diff:
        access_attempt = md.AccessAttempt(
            login_session_id=login_session_id,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.AccessAttemptResult.PERMISSION_DENIED.value)
        db_session.add(access_attempt)
        await db_session.commit()
        raise fs.HTTPException(
            status_code=fs.status.HTTP_403_FORBIDDEN,
            detail=list(diff))
    requested_permissions = set(p for p in user_permissions if p.name in requested_permissions_names)
    permission_min_time = min(requested_permissions, key=lambda x: x.expiration_min)
    min_time = min(divmod((session_token.exp - datetime.now()).total_seconds(), 60)[0], permission_min_time.expiration_min) 
    expire_at = datetime.utcnow() + timedelta(minutes=min_time)
    access_session = md.AccessSession(
        login_session_id=login_session_id,
        start=datetime.utcnow(),
        end=expire_at)
    db_session.add(access_session)
    access_attempt = md.AccessAttempt(
        login_session_id=login_session_id,
        fingerprint=request.client.host,  # type: ignore
        date_time=datetime.utcnow(),
        response=sh.AccessAttemptResult.SUCCESS.value)
    db_session.add(access_attempt)
    await db_session.commit()
    user = await b.user_by_id(db_session, session_token.sub)
    access_token_data = sh.AccessTokenData(
        jti=access_session.id,  # type: ignore
        sub=user.external_id,  # type: ignore
        pms=permissions,
        exp=expire_at)
    return sh.Token(
        token=sec.create_access_token(access_token_data.dict()),
        type=sh.TokenType.ACCESS)
    


@access_sessions_router.get('/{id}', response_model=sh.AccessSession)
async def access_session_data(
    id: int = fs.Path(ge=0),
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> md.AccessSession:
    return await b.access_session_by_id(db_session, id)
