from __future__ import annotations

from datetime import datetime
from enum import Enum, auto, StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, Field
from utils import str_to_type, type_key


class HasUUID(Protocol):
    """
    to create redis key as classname:uuid
    """
    uuid: UUID


# from auth
PermissionName = str


# from auth
class AccessTokenData(BaseModel):
    jti: int = Field(ge=0, default=0)
    sub: int = Field(ge=0, default=0)
    pms: list[PermissionName]
    exp: datetime


class UserStatus(Enum):
    """
    fot future away, typing...
    """
    OFFLINE = 'OFFLINE'
    ONLINE = 'ONLINE'


class User(BaseModel):
    """
    simple user model to determinate message sender in chat
    """
    id: int
    name: str

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.id))

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, User):
            raise TypeError(
                f'Object of type {__o.__class__.__name__} can\'t be compared to Chat object')
        return self.id == __o.id


class UserInfo(BaseModel):
    """
    extended user model
    """
    pass


class Chat(BaseModel):
    """
    chat information model
    """
    uuid: UUID
    name: str
    owner: int  # User id

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.uuid) + self.name)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Chat):
            raise TypeError(
                f'Object of type {__o.__class__.__name__} can\'t be compared to Chat object')
        return self.uuid == __o.uuid and self.name == __o.name


class MessageStatus(Enum):
    SENT = 'SENT'
    DELIVERED = 'DELIVERED'
    READ = 'READ'


"""
User sends message with receiver, status=SENT, text not Null, uuid and sender are Null (set by BE app)
check if user is allowed to send messages to the receiver Chat
BE set message uuid and sender
publish to receiver Chat channel
save with key message:uuid = receiver
reader receives the message
reader responses with status=DELIVERED, uuid other = Null
be gets message from redis
BE checks that the reader it allowed to read the chat
be publish message
subscriber updates message status
"""


class Message(BaseModel):
    receiver: UUID  # Chat uuid
    status: MessageStatus
    sender: User
    text: str
    uuid: UUID


class NewMessage(BaseModel):
    receiver: UUID  # Chat uuid
    text: str


class UpdateMessage(BaseModel):
    status: MessageStatus
    uuid: UUID


class CachedMessage(BaseModel):
    receiver: UUID  # Chat uuid
    status: MessageStatus
    sender: User
    uuid: UUID

# on login get user access permissions
# auth service add to cache as permission:user_uuid:resource_class_name:resource_uuid = level with expiration time
# when user needs additional resource. user makes access request
# auth service adds new key to redis with expiration time
# on logout delete all keys
# to revoke access auth service deletes key


class AccessRequest(BaseModel):
    resource: UUID
    level: RoleLevel
    # user: UUID | None = None


class Permission(BaseModel):
    user_uuid: UUID
    resource_type: type
    resource_uuid: UUID

    @property
    def key(self) -> str:
        return (f'{type_key(self.__class__)}:{self.user_uuid}'
                f':{self.resource_type}:{self.resource_uuid}')

    @property
    def resource_key(self) -> str:
        return f':{self.resource_type}:{self.resource_uuid}'

    @staticmethod
    def from_str(permission: str) -> Permission:
        keys = permission.split(':')
        return Permission(user_uuid=UUID(keys[1]),
                          resource_type=str_to_type(keys[2]),
                          resource_uuid=UUID(keys[3]))

    @staticmethod
    def update_channel(user: UUID) -> str:
        return f'{type_key(Permission)}:update:{user}'


# class AccessLevel:
#     resource: UUID
#     user: UUID
#     role: UserRole

# class UserType(Enum):
#     UNKNOWN = 'UNKNOWN'
#     USER = 'USER'
#     ADMIN = 'ADMIN'
#     MODERATOR = 'MODERATOR'

class RoleLevel(StrEnum):
    UNSET = auto()
    BANNED = auto()
    READER = auto()
    WRITER = auto()
    MODERATOR = auto()
    ADMIN = auto()

class Role(BaseModel):
    resource: HasUUID
    user: int
    level: RoleLevel
    
    @property
    def redis_key(self):
        return f'{self.key_prefix}:{self.user}:{self.resource.uuid}'
    
    @property
    @classmethod
    def key_prefix(cls):
        return cls.__name__
