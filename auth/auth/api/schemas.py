from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

TOKEN_NAME = 'App-Token'


class LoginAttemptResult(Enum):
    SUCCESS = 'SUCCESS'
    LIMIT_REACHED = 'LIMIT_REACHED'
    INCORRECT_LOGIN = 'INCORRECT_LOGIN'
    INCORRECT_PASSWORD = 'INCORRECT_PASSWORD'


class AccessAttemptResult(Enum):
    SUCCESS = 'SUCCESS'
    EXPIRED_TOKEN = 'EXPIRED_TOKEN'
    BLOCKED_TOKEN = 'BLOCKED_TOKEN'
    INVALID_TOKEN = 'INVALID_TOKEN'
    PERMISSION_DENIED = 'PERMISSION_DENIED'


class TokenType(Enum):
    ACCESS = 'ACCESS'
    REFRESH = 'REFRESH'


class RegistrationData(BaseModel):
    external_id: int = Field(ge=0)
    login: str = Field(max_length=32)
    password: str = Field(max_length=128)

    class Config:
        orm_mode = True


class LoginData(BaseModel):
    login: str | None = Field(max_length=32)
    password: str | None = Field(max_length=128)

    class Config:
        orm_mode = True


class UserData(BaseModel):
    id: int = Field(ge=0)
    external_id: int = Field(ge=0)
    login: str = Field(max_length=32)
    confirmed: bool
    created_timestamp: datetime

    class Config:
        orm_mode = True


class AccessSession(BaseModel):
    id: int = Field(ge=0)
    login_session_id: int = Field(ge=0)
    start: datetime
    end: datetime
    stopped: bool

    class Config:
        orm_mode = True


class LoginSession(BaseModel):
    id: int = Field(ge=0)
    user_id: int = Field(ge=0)
    start: datetime
    end: datetime
    stopped: bool

    class Config:
        orm_mode = True


class Permission(BaseModel):
    name: str = Field(max_length=128)
    expiration_min: int = Field(ge=1)

    class Config:
        orm_mode = True


PermissionName = str

class Service(BaseModel):
    name: str = Field(max_length=128)
    key: str = Field(max_length=256)

    class Config:
        orm_mode = True


class AccessTokenData(BaseModel):
    jti: int = Field(ge=0)
    sub: int = Field(ge=0)
    pms: list[PermissionName]
    exp: datetime


class SessionTokenData(BaseModel):
    jti: int = Field(ge=0)
    sub: int = Field(ge=0)
    exp: datetime


class Token(BaseModel):
    token: str = Field(max_length=512)
    type: TokenType


class Key(BaseModel):
    key: str = Field(max_length=256)