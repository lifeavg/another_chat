import dataclasses as dcl
from datetime import datetime, timedelta

import fastapi as fs

import auth.api.base as b
import auth.api.schemas as sh
import auth.db.connection as con
import auth.db.models as md
import auth.db.query as dq
import auth.security as sec

sign_router = fs.APIRouter(tags=['user_identification'])


@sign_router.post('/signup', status_code=201, response_model=sh.UserData)
async def signup(
    registration_data: sh.RegistrationData,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> md.User:
    await b.check_user_exists(registration_data, db_session)
    b.validate_new_password(registration_data)
    return await b.create_new_user(registration_data, db_session)


@sign_router.post('/signin', response_model=sh.Token)
async def signin(
    login_data: sh.LoginData,
    request: fs.Request,
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> sh.Token:
    limit_delay = await sec.login_limit(db_session, request.client.host)  # type: ignore
    if limit_delay:
        login_attempt = md.LoginAttempt(
            login_data_id=None,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.LIMIT_REACHED.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise fs.HTTPException(status_code=fs.status.HTTP_429_TOO_MANY_REQUESTS,
                               detail='Login attempts limit reached',)
    user = await dq.user_by_login(db_session, login_data. login)  # type: ignore
    if not user:
        login_attempt = md.LoginAttempt(
            login_data_id=None,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.INCORRECT_LOGIN.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise fs.HTTPException(status_code=fs.status.HTTP_401_UNAUTHORIZED,
                               detail='Incorrect username or password',
                               headers={'WWW-Authenticate': sh.TOKEN_NAME},)
    if not sec.verify_password(login_data.password, user.password):  # type: ignore
        login_attempt = md.LoginAttempt(
            login_data_id=user.id,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.INCORRECT_PASSWORD.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise fs.HTTPException(status_code=fs.status.HTTP_401_UNAUTHORIZED,
                               detail='Incorrect username or password',
                               headers={'WWW-Authenticate': sh.TOKEN_NAME},)
    login_attempt = md.LoginAttempt(
        login_data_id=user.id,
        fingerprint=request.client.host,  # type: ignore
        date_time=datetime.utcnow(),
        response=sh.LoginAttemptResult.SUCCESS.value)
    db_session.add(login_attempt)
    token_start = datetime.utcnow()
    token_expires = token_start + \
        timedelta(minutes=sec.SEC_ACCESS_EXPIRE_MINUTES)
    session = md.LoginSession(user_id=user.id, start=token_start,
                              end=token_expires)  # type: ignore
    db_session.add(session)
    await db_session.commit()
    token = sec.create_access_token(data=dcl.asdict(sh.SessionTokenData(
        jti=session.id, sub=user.external_id, exp=token_expires)))  # type: ignore
    return sh.Token(token=token, type=sh.TokenType.REFRESH)


@sign_router.post('/signout', response_class=fs.Response)
async def signout(
    db_session: con.AsyncSession = fs.Depends(con.get_db_session)
) -> None:
    session_token = sh.SessionTokenData(jti=1, sub=1, exp = datetime.now())
    login_sessions = await dq.user_login_sessions(db_session, session_token.sub, 200, 0, True)
    for session in login_sessions:
        session.stopped = True  # type: ignore
        session.end = datetime.utcnow()  # type: ignore
