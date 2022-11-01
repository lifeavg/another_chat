from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from db import AsyncSession, get_login_limit_by_fingerprint

SEC_SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
SEC_ALGORITHM = "HS256"
SEC_TOKEN_EXPIRE_MINUTES = 30
SEC_ATTEMPT_DELAY_MINUTES = 10
SEC_MAX_ATTEMPT_DELAY_COUNT = 5

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict,
                        expires: datetime,
                        secret: str = SEC_SECRET_KEY,
                        algorithm: str = SEC_ALGORITHM
                        ) -> str:
    data.update({"exp": expires})
    encoded_jwt = jwt.encode(data, secret, algorithm)
    return encoded_jwt

async def login_limit(session: AsyncSession,
                      fingerprint: str,
                      delay_minutes: int = SEC_ATTEMPT_DELAY_MINUTES,
                      max_attempts: int = SEC_MAX_ATTEMPT_DELAY_COUNT) -> timedelta | None:
    attempts = await get_login_limit_by_fingerprint(session, fingerprint, delay_minutes)
    if len(attempts) >= max_attempts:
        return timedelta(minutes=delay_minutes) - (datetime.utcnow() - attempts[0].date_time())

def password_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'


# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_data = TokenData(username=username)
#     except JWTError:
#         raise credentials_exception
#     user = get_user(fake_users_db, username=token_data.username)
#     if user is None:
#         raise credentials_exception
#     return user


# async def get_current_active_user(current_user: User = Depends(get_current_user)):
#     if current_user.disabled:
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user
