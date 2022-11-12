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

@app.post("/activate?id=ghjghjghj")
async def activate():
    """activate new created account"""
    pass

@app.post("/deactivate?id=ghjghjghj")
async def deactivate():
    """deactivate account"""
    pass

@app.get("/user")
async def user_information():
    """get user account information"""
    pass

@app.put("/user")
async def update_user():
    """update user information"""
    pass

@app.post("/delete?=id")
async def delete_user():
    """delete user from system"""
    pass

@app.get("/user_sessions?active=true|false|null")
async def get_user_sessions():
    """list of user sessions"""
    pass

@app.post("/terminate")
async def terminate():
    """terminate user sessions from request"""
    pass