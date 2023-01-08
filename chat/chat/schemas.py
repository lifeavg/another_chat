from datetime import datetime
from enum import StrEnum, auto
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


@runtime_checkable
class _IIntID(Protocol):
    @property
    def id(self) -> int:  # type: ignore
        pass


@runtime_checkable
class _IStrID(Protocol):
    @property
    def id(self) -> str:  # type: ignore
        pass


@runtime_checkable
class _IUuidId(Protocol):
    @property
    def id(self) -> UUID:  # type: ignore
        pass


IResource = _IIntID | _IStrID | _IUuidId
ResourceId = UUID | str | int


class ResourceMeta(BaseModel):
    type: type
    id: ResourceId = 0


# from auth
PermissionName = str


# from auth
class AccessTokenData(BaseModel):
    jti: int = Field(ge=0, default=0)
    sub: int = Field(ge=0, default=0)
    pms: list[PermissionName]
    exp: datetime


_cmp_RoleLevel = (
    'unset',
    'banned',
    'reader',
    'writer',
    'moderator',
    'admin'
)


class RoleLevel(StrEnum):
    UNSET = auto()
    BANNED = auto()
    READER = auto()
    WRITER = auto()
    MODERATOR = auto()
    ADMIN = auto()

    def __lt__(self, other: object) -> bool:
        if isinstance(other, RoleLevel):
            print(_cmp_RoleLevel.index(self.value),
                  _cmp_RoleLevel.index(other.value))
            return _cmp_RoleLevel.index(self.value) < _cmp_RoleLevel.index(other.value)
        raise TypeError

    def __le__(self, other: object) -> bool:
        if isinstance(other, RoleLevel):
            print(_cmp_RoleLevel.index(self.value),
                  _cmp_RoleLevel.index(other.value))
            return _cmp_RoleLevel.index(self.value) <= _cmp_RoleLevel.index(other.value)
        raise TypeError

    def __gt__(self, other: object) -> bool:
        if isinstance(other, RoleLevel):
            print(_cmp_RoleLevel.index(self.value),
                  _cmp_RoleLevel.index(other.value))
            return _cmp_RoleLevel.index(self.value) > _cmp_RoleLevel.index(other.value)
        raise TypeError

    def __ge__(self, other: object) -> bool:
        if isinstance(other, RoleLevel):
            print(_cmp_RoleLevel.index(self.value),
                  _cmp_RoleLevel.index(other.value))
            return _cmp_RoleLevel.index(self.value) >= _cmp_RoleLevel.index(other.value)
        raise TypeError


class Role(BaseModel):
    resource_meta: ResourceMeta
    user_id: int = 0
    level: RoleLevel = RoleLevel.BANNED

    class Config:
        arbitrary_types_allowed = True

    @property
    def redis_key(self):
        return f'{self.key_prefix}:{self.user_id}:{self.resource_meta.type}:{self.resource_meta.id}'

    @classmethod
    @property
    def key_prefix(cls):
        return cls.__name__


class User(BaseModel):
    id: int = 0
    name: str = ''

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.id))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            raise TypeError(
                f'Object of type {other.__class__.__name__} can\'t be compared to Chat object')
        return self.id == other.id

    @property
    def redis_key(self):
        return f'{self.key_prefix}:{self.id}'

    @classmethod
    @property
    def key_prefix(cls):
        return cls.__name__


class UserStatus(StrEnum):
    OFFLINE = auto()
    ONLINE = auto()


class Chat(BaseModel):
    id: int = 0
    name: str = ''
    owners: tuple[int, ...] = Field(default_factory=tuple)

    def __hash__(self) -> int:
        return hash(self.__class__.__name__ + str(self.id) + self.name)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Chat):
            raise TypeError(
                f'Object of type {__o.__class__.__name__} can\'t be compared to Chat object')
        return self.id == __o.id and self.name == __o.name


class Message(BaseModel):
    receiver: int = 0
    sender: int = 0
    text: str = ''
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def redis_key(self):
        return f'{self.key_prefix}:{self.id}'

    @classmethod
    @property
    def key_prefix(cls):
        return cls.__name__


class Command(StrEnum):
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()


class Request(BaseModel):
    command: Command
    resource: IResource | None
    parameters: dict[str, Any] = Field(default_factory=dict)
    id: str = ''


class Notification(BaseModel):
    resource: list[IResource] = Field(default_factory=list)
    result: bool = False
    id: str = ''
