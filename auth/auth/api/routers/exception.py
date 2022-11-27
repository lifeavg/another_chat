from typing import Any

from fastapi import HTTPException, status

from auth.api.schemas import TOKEN_NAME, PermissionName


class IntegrityError(HTTPException):
    def __init__(self, detail: str) -> None:
        pos = detail.find('DETAIL:  ') + len('DETAIL:  ')
        super().__init__(
            status.HTTP_409_CONFLICT,
            detail[pos:len(detail)])


class LoginLimitReached(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            'Login attempts limit reached')


class DataNotFound(HTTPException):
    def __init__(self, missing_data: list[Any]) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, missing_data)


class NotSecureKey(HTTPException):
    def __init__(self, reason: str) -> None:
        super().__init__(status.HTTP_409_CONFLICT, reason)


class AuthorizationError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED,
            'Incorrect username or password',
            {'WWW-Authenticate': TOKEN_NAME})


class ParameterRequeued(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            'Specify at least one parameter')


class NoPermission(HTTPException):
    def __init__(self, permissions: list[PermissionName]) -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, permissions)


class SingleServiceAllowed(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            'Token issued only for single service')
