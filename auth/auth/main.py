from datetime import timedelta, datetime

from fastapi import Depends, FastAPI, HTTPException, status, Request, Response

from .security import (SEC_ACCESS_EXPIRE_MINUTES, verify_password,
                      create_access_token, login_limit, new_password_validator,
                      password_hash)
import db
import schemas as sh
import models as md


app = FastAPI()

@app.post("/signout")
async def sign_out():
    """sign out from current session"""
    pass

@app.post('/signin')
async def sign_in(request: Request,
                  response: Response,
                  form_data: sh.LoginData,
                  db_session: db.AsyncSession = Depends(db.get_db_session)
                  ) -> sh.Token:
    """sign into existing account"""
    limit_delay = await login_limit(db_session, request.client.host)  # type: ignore
    if limit_delay:
        login_attempt = md.LoginAttempt(login_data_id=None,
                                     fingerprint=request.client.host,  # type: ignore
                                     date_time=datetime.utcnow(),
                                     response=sh.LoginAttemptResult.LIMIT_REACHED.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail='Login attempts limit reached',)
    user = await db.get_login_data_by_username(db_session, form_data.username)
    if not user:
        login_attempt = md.LoginAttempt(login_data_id=None,
                                     fingerprint=request.client.host,  # type: ignore
                                     date_time=datetime.utcnow(),
                                     response=sh.LoginAttemptResult.INCORRECT_LOGIN.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Incorrect username or password',
                            headers={'WWW-Authenticate': sh.TOKEN_TYPE},)
    if not verify_password(form_data.password, user.password):  # type: ignore
        login_attempt = md.LoginAttempt(login_data_id=user.id,
                                     fingerprint=request.client.host,  # type: ignore
                                     date_time=datetime.utcnow(),
                                     response=sh.LoginAttemptResult.INCORRECT_PASSWORD.value)
        db_session.add(login_attempt)
        await db_session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Incorrect username or password',
                            headers={'WWW-Authenticate': sh.TOKEN_TYPE},)
    login_attempt = md.LoginAttempt(login_data_id=user.id,
                                 fingerprint=request.client.host,  # type: ignore
                                 date_time=datetime.utcnow(),
                                 response=sh.LoginAttemptResult.SUCCESS.value)
    db_session.add(login_attempt)
    access_token_start = datetime.utcnow()
    access_token_expires = access_token_start + timedelta(minutes=SEC_ACCESS_EXPIRE_MINUTES)
    access_token = create_access_token(data={'sub': user.user_id}, expires=access_token_expires)
    login_session = md.LoginSession(login_data_id=user.id,
                                 start=access_token_start,
                                 end=access_token_expires)
    db_session.add(login_session)
    await db_session.commit()
    return sh.Token

@app.post("/signup", response_model=dict[str, int])
async def sign_up(registration_data: sh.LoginData,
                          db_session: db.AsyncSession = Depends(db.get_db_session)
                          ) -> dict[str, int]:
    """create a new account in inactive status"""
    user = await db.get_login_data_by_username(db_session,
                                         registration_data.username)
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Login already exists',)
    valid, reason = new_password_validator(registration_data.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=reason,)
    login_data = md.User(user_id=registration_data.user_id,
                           login=registration_data.username,
                           password=password_hash(registration_data.password))
    db_session.add(login_data)
    await db_session.commit()
    return {'login_id': login_data.id}  # type: ignore


class RegistrationData:
    external_id:int
    login: str
    password: str

class LoginData:
    login: str
    password: str

class UserData:
    id: int
    external_id: int
    login: str
    confirmed: bool
    created_timestamp: datetime


class AccessSession:
    id: int
    login_session_id: int
    start: datetime
    end: datetime
    stopped: bool

class LoginSession:
    id: int
    user_id: int
    start: datetime
    end: datetime | None
    stopped: bool


class AccessToken:
    access_token: str
    # 
    id: int
    external_id: int
    permissions: list
    end: datetime
    

class SessionToken:
    session_token: str
    id: int
    user_id: int
    end: datetime


class Permission:
    id: int
    name: str
    service_id: int

class PermissionName:
    permissuion: str

class Service:
    id: int
    name: str
    key: str
    permissions: list[PermissionName]

@app.post("/signup")
async def _(user: RegistrationData) -> UserData:
    pass

@app.get("/users/id")
async def _(id: int) -> UserData:
    pass

@app.get("/users/id/permissions")
async def _(id: int) -> list[PermissionName]:
    pass

@app.post("/users/id/permissions/add")
async def _(id: int, permissions: list[PermissionName]) -> list[PermissionName]:
    pass

@app.post("/users/id/permissions/remove")
async def _(id: int, permissions: list[PermissionName]) -> list[PermissionName]:
    pass

@app.get("/users/id/login_sessions?active")
async def _(id: int, active: bool | None = None) -> list[LoginSession]:
    pass

@app.post('/signin')
async def _(login: LoginData) -> SessionToken:
    pass

@app.put("/users/id?confirmed=[true|false], active=[true|false]")
async def _(id: int, confirmed: bool | None = None, active: bool | None = None):
    pass

@app.post("/users/id/update")
async def _(login: LoginData):
    pass

@app.delete("/users/id")
async def _(id: int):
    pass

############################


@app.get("/login_sessions/id")
async def _(id: int) -> LoginSession:
    pass

@app.get("/login_sessions/id/access_sessions?active")
async def _(id: int, active: bool | None = None) -> list[AccessSession]:
    pass

@app.post("/login_sessions/id/terminate")
async def _(id: int):
    pass

#######################################

@app.post('/access_sessions')
async def _(permission: list[Permission]) -> AccessToken:
    pass

@app.get('/access_sessions/id')
async def _(id: int):
    pass

#######################################

@app.get('/services/service_name')
async def _(name: str) -> Service:
    pass

@app.post('/services/service_name/permissions')
async def _(name: str) -> list[PermissionName]:
    pass

@app.get('/services/service_name/permissions')
async def _(name: str) -> list[PermissionName]:
    pass

@app.delete('/services/service_name/permissions/permission_name')
async def _(service_name: str, permission_name: str):
    pass

@app.put('/services/service_name?key')
async def _(service_name: str, key: str):
    pass

#######################################

@app.get('/permissions/permission_name')
async def _(permission_name: str) -> Permission:
    pass
