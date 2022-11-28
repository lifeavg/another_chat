from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LoginAttemptResult(Enum):
    SUCCESS = 'SUCCESS'
    LIMIT_REACHED = 'LIMIT_REACHED'
    INCORRECT_LOGIN = 'INCORRECT_LOGIN'
    INCORRECT_PASSWORD = 'INCORRECT_PASSWORD'


class AccessAttemptResult(Enum):
    SUCCESS = 'SUCCESS'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    SINGLE_SERVICE = 'SINGLE_SERVICE'


class TokenType(Enum):
    ACCESS = 'ACCESS'
    SESSION = 'SESSION'


class Login(BaseModel):
    login: str = Field(max_length=32)
    password: str = Field(max_length=128)

    class Config:
        orm_mode = True


class User(BaseModel):
    id: int = Field(ge=0)
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
