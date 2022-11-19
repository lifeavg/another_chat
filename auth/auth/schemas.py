from dataclasses import dataclass
from enum import Enum
from datetime import datetime

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

@dataclass
class RegistrationData:
    external_id:int
    login: str
    password: str

@dataclass
class LoginData:
    login: str
    password: str

@dataclass
class UserData:
    id: int
    external_id: int
    login: str
    confirmed: bool
    created_timestamp: datetime

@dataclass
class AccessSession:
    id: int
    login_session_id: int
    start: datetime
    end: datetime
    stopped: bool

@dataclass
class LoginSession:
    id: int
    user_id: int
    start: datetime
    end: datetime | None
    stopped: bool

@dataclass
class Permission:
    id: int
    name: str
    service_id: int

@dataclass
class PermissionName:
    permission: str

@dataclass
class Service:
    id: int
    name: str
    key: str
    permissions: list[PermissionName]
    
@dataclass
class AccessTokenData:
    jti: int
    sub: int
    pms: list[PermissionName]
    exp: datetime
    
@dataclass
class SessionTokenData:
    jti: int
    sub: int
    exp: datetime

@dataclass
class Token:
    token: str
    type: TokenType