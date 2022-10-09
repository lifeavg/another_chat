
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, AuthenticationError, BaseUser
)
import base64
import binascii
from uuid import UUID, uuid4


from starlette.authentication import requires
from schemas import User, Chat

class AuthenticatedUser(BaseUser):
    
    def __init__(self) -> None:
        super().__init__()
        self.user = User(uuid=uuid4(), name='username aaaaaa')

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return 'username aaaaaa'

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


