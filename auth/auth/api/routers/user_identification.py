from datetime import datetime, timezone

import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq
import auth.security as sec

sign_router = fs.APIRouter(tags=['user_identification'])


@sign_router.post('/signup', status_code=fs.status.HTTP_201_CREATED, response_model=sh.User)
async def signup(
    registration_data: sh.Login,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> md.User:
    b.validate_new_password(registration_data)
    return await b.create_new_user(registration_data, db_session)


@sign_router.post('/signin', response_model=sh.Token)
async def signin(
    login_data: sh.Login,
    request: fs.Request,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Token:
    await b.check_login_limit(request, db_session)
    user = await dq.user_by_login(db_session, login_data.login)
    await b.check_login_data(login_data, user, db_session, request)
    b.add_login_attempt(request, db_session, user=user)
    session = b.add_login_session(user, db_session)
    await db_session.commit()
    return b.create_session_token(session)


@sign_router.post('/signout', response_class=fs.Response)
async def signout(
    db_session: con.AsyncSession = fs.Depends(con.get_db_session),
    token: sh.SessionTokenData = fs.Depends(
        sec.TokenAuth(tuple(), sh.SessionTokenData))
) -> None:
    login_sessions = await dq.user_login_sessions(
        db_session, token.sub, 200, 0, True)
    for session in login_sessions:
        session.stopped = True  # type: ignore
        session.end = datetime.now(timezone.utc)  # type: ignore
    await db_session.commit()
