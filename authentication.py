
import base64
import binascii
from uuid import UUID, uuid4

from redis.asyncio.client import Redis
from starlette.authentication import (AuthCredentials, AuthenticationBackend,
                                      AuthenticationError, BaseUser)

from schemas import Permission, User
from utils import type_key


class AuthenticatedUser(BaseUser):

    def __init__(self) -> None:
        super().__init__()
        self.user = User(uuid=uuid4(), name='username aaaaaa')

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.user.name

    @property
    def uuid(self) -> UUID:
        return self.user.uuid

    # @property
    # def identity(self) -> str:
    #     raise NotImplementedError()  # pragma: no cover


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return

        auth = conn.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != 'basic':
                return
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError('Invalid basic auth credentials')

        username, _, password = decoded.partition(":")
        # TODO: You'd want to verify the username and password here.
        return AuthCredentials(["authenticated"]), AuthenticatedUser()


class SecurityManager:

    def __init__(self, redis: Redis) -> None:
        self.redis: Redis = redis

    async def load_channels_from_permissions(self, user: User,
                                             resource_type: type,
                                             existing_channels: set[str]) -> tuple[set[str], set[str]]:
        new_channels = set()
        async for permission_data in self.redis.scan_iter(f'{type_key(Permission)}:{user.uuid}'):
            permission = Permission.from_str(permission_data)
            if permission.resource_type == type_key(resource_type):
                new_channels.add(new_channels)
                existing_channels.discard(permission.resource_key)
        new_channels.add(
            'chat:3a78e770-6789-4e4a-9286-73ee6cd283a6')  # TODO remove
        return new_channels, existing_channels

    async def is_permitted(self, permission: Permission) -> bool:
        if await self.redis.get(permission.key):
            return True
        return True  # TODO False
