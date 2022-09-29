from enum import Enum
from typing import Protocol
from uuid import UUID

from pydantic.dataclasses import dataclass


class HasUUID(Protocol):
    uuid: UUID


@dataclass
class Chat:
    uuid: UUID
    name: str

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.uuid) + self.name)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Chat):
            raise TypeError(
                f'Object of type {__o.__class__.__name__} can\'t be compared to Chat object')
        return self.uuid == __o.uuid and self.name == __o.name


@dataclass
class User:
    uuid: UUID
    name: str


@dataclass
class Message:
    uuid: UUID | None
    sender: User | None
    receiver: Chat
    text: str


@dataclass
class Subscription:
    user: User
    chats: list[Chat]
    subscribe: bool


class Status(Enum):
    DELIVERED = 'DELIVERED'
    READ = 'READ'
    SUBSCRIBED = 'SUBSCRIBED'


@dataclass
class Confirmation:
    uuid: UUID
    status: Status
