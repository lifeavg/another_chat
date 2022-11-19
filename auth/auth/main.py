from datetime import timedelta, datetime
from dataclasses import asdict
from fastapi import Depends, FastAPI, HTTPException, status, Request, Response

from .security import (SEC_ACCESS_EXPIRE_MINUTES, verify_password,
                      create_access_token, login_limit, new_password_validator,
                      password_hash)
import db
import schemas as sh
import models as md


app = FastAPI()

@app.post('/signup')
async def signup(registration_data: sh.RegistrationData,
                 db_session: db.AsyncSession = Depends(db.get_db_session)
                 ) -> sh.UserData:
    existing_user = await db.user_by_login(db_session, registration_data.login)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Login already exists',)
    valid, reason = new_password_validator(registration_data.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=reason,)
    new_user = md.User(external_id=registration_data.external_id,
                       login=registration_data.login,
                       password=password_hash(registration_data.password))
    db_session.add(new_user)
    await db_session.commit()
    user = await db.user_by_login(db_session, registration_data.login)
    return sh.UserData(id=user.id, external_id=user.external_id, login=user.login, confirmed=user.confirmed, created_timestamp=user.created_timestamp)  # type: ignore

@app.get('/users/{id}')
async def user_data(id: int) -> sh.UserData:
    pass

@app.get('/users/{id}/permissions')
async def user_permissions(id: int) -> list[sh.PermissionName]:
    pass

@app.post('/users/{id}/permissions/add')
async def add_user_permissions(id: int, permissions: list[sh.PermissionName]) -> list[sh.PermissionName]:
    pass

@app.post('/users/{id}/permissions/remove')
async def remove_user_permissions(id: int, permissions: list[sh.PermissionName]) -> list[sh.PermissionName]:
    pass

@app.get('/users/{id}/login_sessions')
async def user_login_sessions(id: int, active: bool | None = None) -> list[sh.LoginSession]:
    pass

@app.post('/signin')
async def signin(login_data:sh.LoginData,
                 request: Request,
                 db_session: db.AsyncSession = Depends(db.get_db_session)
                 ) -> sh.Token:
    limit_delay = await login_limit(db_session, request.client.host)  # type: ignore
    if limit_delay:
        login_attempt = md.LoginAttempt(
            login_data_id=None,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.LIMIT_REACHED.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail='Login attempts limit reached',)
    user = await db.user_by_login(db_session, login_data.login)
    if not user:
        login_attempt = md.LoginAttempt(
            login_data_id=None,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.INCORRECT_LOGIN.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Incorrect username or password',
                            headers={'WWW-Authenticate': sh.TOKEN_NAME},)
    if not verify_password(login_data.password, user.password):  # type: ignore
        login_attempt = md.LoginAttempt(
            login_data_id=user.id,
            fingerprint=request.client.host,  # type: ignore
            date_time=datetime.utcnow(),
            response=sh.LoginAttemptResult.INCORRECT_PASSWORD.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Incorrect username or password',
                            headers={'WWW-Authenticate': sh.TOKEN_NAME},)
    login_attempt = md.LoginAttempt(
        login_data_id=user.id,
        fingerprint=request.client.host,  # type: ignore
        date_time=datetime.utcnow(),
        response=sh.LoginAttemptResult.SUCCESS.value)
    db_session.add(login_attempt)
    token_start = datetime.utcnow()
    token_expires = token_start + timedelta(minutes=SEC_ACCESS_EXPIRE_MINUTES)
    session = md.LoginSession(
        user_id=user.id,
        start=token_start,
        end=token_expires)
    db_session.add(session)
    await db_session.commit()
    token = create_access_token(data=asdict(sh.SessionTokenData(jti=session.id, sub=user.external_id, exp=token_expires)))  # type: ignore
    return sh.Token(token=token, type=sh.TokenType.REFRESH)

@app.put('/users/{id}')
async def update_user_state(id: int,
                            confirmed: bool | None = None,
                            active: bool | None = None):
    pass

@app.post('/users/{id}/update')
async def update_user_data(login: sh.LoginData):
    pass

@app.delete('/users/{id}')
async def delete_user(id: int):
    pass

############################


@app.get('/login_sessions/{id}')
async def login_session_data(id: int) -> sh.LoginSession:
    pass

@app.get('/login_sessions/{id}/access_sessions')
async def login_session_access_sessions(id: int, active: bool | None = None) -> list[sh.AccessSession]:
    pass

@app.post('/login_sessions/{id}/terminate')
async def terminate_login_session(id: int):
    pass

@app.post('/signout')
async def signout():
    pass

#######################################

@app.post('/access_sessions')
async def get_access_session(permission: list[sh.Permission]) -> sh.Token:
    pass

@app.get('/access_sessions/{id}')
async def access_session_data(id: int):
    pass

#######################################

@app.get('/services/{service_name}')
async def service_data(name: str) -> sh.Service:
    pass

@app.post('/services/{service_name}/permissions')
async def add_service_permissions(name: str) -> list[sh.PermissionName]:
    pass

@app.get('/services/{service_name}/permissions')
async def service_permissions(name: str) -> list[sh.PermissionName]:
    pass

@app.delete('/services/{service_name}/permissions/{permission_name}')
async def delete_service_permission(service_name: str, permission_name: str):
    pass

@app.put('/services/{service_name}')
async def update_service_key(service_name: str, key: str):
    pass

#######################################

@app.get('/permissions/{permission_name}')
async def permission_data(permission_name: str) -> sh.Permission:
    pass
