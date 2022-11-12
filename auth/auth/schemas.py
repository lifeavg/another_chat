from dataclasses import dataclass
from enum import Enum

TOKEN_TYPE = 'App-Token'


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

@dataclass
class Token:
    access_token: str
    token_type: str = TOKEN_TYPE


@dataclass
class LoginData:
    user_id: int
    username: str
    password: str
