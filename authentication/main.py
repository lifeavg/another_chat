from datetime import timedelta, datetime

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm

from schemas import Token
from security import (SEC_TOKEN_EXPIRE_MINUTES, verify_password,
                      create_access_token, login_limit, password_validator,
                      password_hash)
from db import get_db_session, AsyncSession, get_login_data_by_login
from schemas import LoginAttemptResult, Registration
from models import LoginData, LoginSession, LoginAttempt


app = FastAPI()


@app.post("/token", response_model=Token)
async def login_for_access_token(request: Request,
                                 form_data: OAuth2PasswordRequestForm = Depends(),
                                 db_session: AsyncSession = Depends(get_db_session)
                                 ) -> Token:
    limit_delay = await login_limit(db_session, request.client.host)
    if limit_delay:
        login_attempt = LoginAttempt(login_data_id=None,
                                     fingerprint=request.client.host,
                                     date_time=datetime.utcnow(),
                                     response=LoginAttemptResult.LIMIT_REACHED.value)
        db_session.add(login_attempt)
        await db_session.commit()
        print(login_attempt)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Login attempts limit reached",)
    user = await get_login_data_by_login(db_session, form_data.username)
    if not user:
        login_attempt = LoginAttempt(login_data_id=None,
                                     fingerprint=request.client.host,
                                     date_time=datetime.utcnow(),
                                     response=LoginAttemptResult.INCORRECT_LOGIN.value)
        db_session.add(login_attempt)
        await db_session.commit()
        print(login_attempt)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"},)
    if not verify_password(form_data.password, user.password):  # type: ignore
        login_attempt = LoginAttempt(login_data_id=user.id,
                                     fingerprint=request.client.host,
                                     date_time=datetime.utcnow(),
                                     response=LoginAttemptResult.INCORRECT_PASSWORD.value)
        db_session.add(login_attempt)
        await db_session.commit()
        print(login_attempt)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"},)
    login_attempt = LoginAttempt(login_data_id=user.id,
                                 fingerprint=request.client.host,
                                 date_time=datetime.utcnow(),
                                 response=LoginAttemptResult.SUCCESS.value)
    db_session.add(login_attempt)
    access_token_start = datetime.utcnow()
    access_token_expires = access_token_start + timedelta(minutes=SEC_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.user_id}, expires=access_token_expires)
    login_session = LoginSession(login_data_id=user.id,
                                 start=access_token_start,
                                 end=access_token_expires)
    db_session.add(login_session)
    await db_session.commit()
    print(login_attempt)
    print(login_session)
    return Token(access_token=access_token, token_type="bearer")

@app.post("/registration", response_model=dict[str, int])
async def create_new_user(registration_data: Registration,
                          db_session: AsyncSession = Depends(get_db_session)
                          ) -> dict[str, int]:
    user = await get_login_data_by_login(db_session,
                                         registration_data.login)
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Login already exists",)
    valid, reason = password_validator(registration_data.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=reason,)
    login_data = LoginData(user_id=registration_data.user_id,
                           login=registration_data.login,
                           password=password_hash(registration_data.password))
    db_session.add(login_data)
    await db_session.commit()
    return {'login_id': login_data.id}  # type: ignore