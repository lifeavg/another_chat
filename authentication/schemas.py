from dataclasses import dataclass
from enum import Enum


class LoginAttemptResult(Enum):
    SUCCESS = 'SUCCESS'
    LIMIT_REACHED = 'LIMIT_REACHED'
    INCORRECT_LOGIN = 'INCORRECT_LOGIN'
    INCORRECT_PASSWORD = 'INCORRECT_PASSWORD'


@dataclass
class Token:
    access_token: str
    token_type: str


@dataclass
class Registration:
    user_id: int
    login: str
    password: str
    

# @dataclass
# class TokenData:
#     username: str | None = None

# @dataclass
# class User:
#     username: str
#     email: str | None = None
#     full_name: str | None = None
#     disabled: bool | None = None
