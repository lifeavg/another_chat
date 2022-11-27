from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

import auth.db.query as dq

SEC_SESSION_EXPIRE_MINUTES = 30
SEC_ATTEMPT_DELAY_MINUTES = 10
SEC_MAX_ATTEMPT_DELAY_COUNT = 5

SEC_ALGORITHM = 'HS256'
SEC_SECRET = b'1234567890'


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    secret: bytes = SEC_SECRET,
    algorithm: str = SEC_ALGORITHM
) -> str:
    encoded_jwt = jwt.encode(data, secret, algorithm)
    return encoded_jwt


async def login_limit(
    session: dq.AsyncSession,
    fingerprint: str,
    delay_minutes: int = SEC_ATTEMPT_DELAY_MINUTES,
    max_attempts: int = SEC_MAX_ATTEMPT_DELAY_COUNT
) -> timedelta | None:
    attempts = await dq.login_attempt_by_fingerprint(
        session, fingerprint, delay_minutes)
    if len(attempts) >= max_attempts:
        return timedelta(minutes=delay_minutes) - \
            (datetime.utcnow() - attempts[0].date_time())


def new_password_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'


def new_key_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'
