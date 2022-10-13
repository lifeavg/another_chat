from __future__ import annotations
from enum import Enum
from typing import Protocol
from uuid import UUID

from pydantic.dataclasses import dataclass


class HasUUID(Protocol):
    """
    to create redis key as classname:uuid
    """
    uuid: UUID

class UserStatus(Enum):
    """
    fot future away, typing...
    """
    OFFLINE = 'OFFLINE'
    ONLINE = 'ONLINE'

@dataclass
class User:
    """
    simple user model to determinate message sender in chat
    """
    uuid: UUID
    name: str

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.uuid))

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Chat):
            raise TypeError(
                f'Object of type {__o.__class__.__name__} can\'t be compared to Chat object')
        return self.uuid == __o.uuid

@dataclass
class UserInfo:
    """
    extended user model
    """
    pass

@dataclass
class Chat:
    """
    chat information model
    """
    uuid: UUID
    name: str
    owner: UUID # User uuid

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

@dataclass
class Message:
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
    receiver: UUID | None # Chat uuid
    status: MessageStatus
    text: str | None = None
    uuid: UUID | None = None
    sender: User | None = None

class AccessLevel(Enum):
    RESTRICTED = 'RESTRICTED'
    READER = 'READER'
    POSTER = 'POSTER'
    MODERATOR = 'MODERATOR'

# on login get user access permissions
# auth service add to cache as permission:user_uuid:resource_class_name:resource_uuid = level with expiration time
# when user needs additional resource. user makes access request
# auth service adds new key to redis with expiration time
# on logout delete all keys 
# to revoke access auth service deletes key
@dataclass
class AccessRequest:
    resource: UUID
    level: AccessLevel
    # user: UUID | None = None

@dataclass
class Permission:
    user_uuid: UUID
    resource_type: str
    resource_uuid: UUID

    @property
    def key(self) -> str:
        return (f'permission:{self.user_uuid}'
                f':{self.resource_type}:{self.resource_uuid}')

    @property
    def resource_key(self) -> str:
        return f':{self.resource_type}:{self.resource_uuid}'

    @staticmethod
    def from_str(permission: str) -> Permission:
        keys = permission.split(':')
        return Permission(user_uuid=UUID(keys[1]),
                          resource_type=keys[2],
                          resource_uuid=UUID(keys[3]))

    @staticmethod
    def update_channel(user: UUID) -> str:
        return f'permission:update:{user}'
        



# @dataclass
# class AccessLevel:
#     resource: UUID
#     user: UUID
#     role: UserRole

# class UserType(Enum):
#     UNKNOWN = 'UNKNOWN'
#     USER = 'USER'
#     ADMIN = 'ADMIN'
#     MODERATOR = 'MODERATOR'
