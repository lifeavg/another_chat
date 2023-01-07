
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from jose import jwt
from jose.exceptions import JWTError
from pydantic.error_wrappers import ValidationError
from redis.asyncio.client import Redis
from schemas import AccessTokenData, Chat, HasUUID, Role, RoleLevel, User
from starlette.authentication import (AuthCredentials, AuthenticationBackend,
                                      AuthenticationError, BaseUser)
from starlette.datastructures import Headers
from starlette.requests import HTTPConnection

# from auth
TOKEN_NAME = 'Bearer'
KEY = b'4354534534'
ALGORITHM = 'HS256'


# from auth
def verify_token(
    token: str,
    expected_type: type,
    secret: bytes,
    algorithm: str
) -> Any:
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_sub": False,
        "verify_jti": False,
        "require_exp": True
    }
    return expected_type(**jwt.decode(token, secret, [algorithm, ], options=options))


class AuthUser(BaseUser):

    def __init__(
        self,
        auth_data: AccessTokenData,
        user: User
    ) -> None:
        super().__init__()
        self._identity: AccessTokenData = auth_data
        self._user = user

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self._user.name

    @property
    def id(self) -> int:
        return self._user.id

    @property
    def identity(self) -> AccessTokenData:
        return self._identity


class AuthenticationManager(AuthenticationBackend):
    def _get_credentials(self, headers: Headers) -> str:
        authorization = headers.get('Authorization')
        if authorization:
            return authorization
        raise AuthenticationError('Authorization requeued')

    def _get_token(self, credentials: str) -> str:
        scheme, token = credentials.split()
        if scheme == TOKEN_NAME:
            return token
        raise AuthenticationError('Invalid authorization scheme')

    def _decrypt_token_data(self, token: str) -> AccessTokenData:
        try:
            return verify_token(token, AccessTokenData, KEY, ALGORITHM)
        except (JWTError, ValidationError):
            raise AuthenticationError('Token decode error')

    def _validate_token_data(self, token_data: AccessTokenData) -> None:
        if token_data.exp < datetime.now(timezone.utc):
            raise AuthenticationError('Token expired')
        if 'chat_access' not in token_data.pms:
            raise AuthenticationError('Permission denied')

    async def authenticate(
        self, connection: HTTPConnection
    ) -> tuple[AuthCredentials, AuthUser] | None:
        token_data = self._decrypt_token_data(
            self._get_token(self._get_credentials(connection.headers)))
        self._validate_token_data(token_data)
        user = User(id=1, name='test_user')  # TODO: get user
        return (AuthCredentials(['authenticated'].append(*token_data.pms)),
                AuthUser(token_data, user))


class RoleManager:

    def __init__(self, redis: Redis, user: User) -> None:
        self.redis: Redis = redis
        self.user: User = user

    async def reload_cache(self) -> tuple[Role, ...]:
        roles = (Role(resource=Chat(uuid=uuid4(), name='chat1', owner=10), user=self.user.id, level=RoleLevel.MODERATOR),  # TODO: load roles
                 Role(resource=Chat(uuid=uuid4(), name='chat2', owner=10), user=self.user.id, level=RoleLevel.MODERATOR))
        await self.clear_cache()
        async with self.redis.pipeline() as pipe:
            for role in roles:
                pipe.set(name=role.redis_key, value=role.level)
            await pipe.execute()
        return roles

    async def clear_cache(self) -> int:
        keys = await self.redis.keys(f'{Role.key_prefix}:{self.user.id}:*')
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def role(self, resource: HasUUID) -> RoleLevel:
        role = await self.redis.get(f'{Role.key_prefix}:{self.user.id}:{resource.uuid}')
        if role is None:
            return RoleLevel.UNSET
        return RoleLevel[role.upper()]

    async def update(self, resource: HasUUID, role: RoleLevel) -> RoleLevel:
        # TODO: implement
        return role
