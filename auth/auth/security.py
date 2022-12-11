from datetime import datetime, timedelta, timezone
from typing import Any

import fastapi as fa
from fastapi.security import HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from pydantic.error_wrappers import ValidationError

import auth.db.query as dq
from auth.api.schemas import AccessTokenData, PermissionName, SessionTokenData

TOKEN_NAME = 'Bearer'

SEC_SESSION_EXPIRE_MINUTES = 30
SEC_ATTEMPT_DELAY_MINUTES = 10
SEC_MAX_ATTEMPT_DELAY_COUNT = 5

SEC_ALGORITHM = 'HS256'
SEC_SECRET_SESSION = b'1234567890'
SEC_SECRET_ACCESS = b'4321qwerty'


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class UnknownTokenType(Exception):
    """No matching key for token"""


class AuthError(fa.HTTPException):
    def __init__(self) -> None:
        super().__init__(
            fa.status.HTTP_403_FORBIDDEN,
            'Invalid authorization code')


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(
    data: dict,
    secret: bytes = SEC_SECRET_SESSION,
    algorithm: str = SEC_ALGORITHM
) -> str:
    return jwt.encode(data, secret, algorithm)


def verify_token(
    token: str,
    expected_type: type,
    secret: bytes,
    algorithm: str = SEC_ALGORITHM
) -> Any:
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_sub": False,
        "verify_jti": False,
        "require_exp": True
    }
    return expected_type(**jwt.decode(token, secret, [algorithm, ], options=options))


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
            (datetime.now(timezone.utc) - attempts[0].date_time)  # type: ignore


def get_key(token_type: type) -> bytes:
    match token_type.__name__:
        case SessionTokenData.__name__:
            return SEC_SECRET_SESSION
        case AccessTokenData.__name__:
            return SEC_SECRET_ACCESS
        case _:
            raise UnknownTokenType()


def new_password_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'


def new_key_validator(password: str) -> tuple[bool, str]:
    # TODO
    return True, 'OK'


class TokenAuth(HTTPBearer):
    def __init__(self,
                 permissions: tuple[PermissionName],
                 token_type: type,
                 ) -> None:
        super().__init__()
        self.permissions = set(permissions)
        self.token_type = token_type
        self.key = get_key(self.token_type)

    async def __call__(self, request: fa.Request) -> SessionTokenData | AccessTokenData:
        credentials = await super().__call__(request)
        if credentials:
            try:
                token = verify_token(
                    credentials.credentials, self.token_type, self.key)
                if token.exp < datetime.now(timezone.utc):
                    raise AuthError()
                if (isinstance(token, AccessTokenData)
                        and not set(self.permissions).issubset(token.pms)):
                    raise AuthError()
                return token
            except JWTError:
                raise AuthError()
            except ValidationError:
                raise AuthError()
        raise AuthError()
