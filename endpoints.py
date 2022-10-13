import asyncio
import json
from dataclasses import asdict
from functools import partial
from typing import Any, Coroutine
from uuid import UUID, uuid4

from pydantic.json import pydantic_encoder
from redis.asyncio.client import PubSub, Redis
from starlette import status
from starlette.authentication import requires
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket

from connections import redis as global_redis
from schemas import Message, MessageStatus, Permission, UserStatus
from utils import to_redis_key

CACHE_EXPIRE_TIME = 18000  # 5h


class ChatEndpoint(WebSocketEndpoint):
    encoding = 'json'

    def __init__(self,
                 scope: Scope,
                 receive: Receive,
                 send: Send,
                 redis: Redis = global_redis) -> None:
        super().__init__(scope, receive, send)
        self.redis: Redis = redis
        self.pubsub: PubSub = self.redis.pubsub()
        self.pubsub_task: asyncio.Task | None = None

    async def guard_resource_permitted(self, websocket: WebSocket, receiver: UUID) -> bool:
        # permission:user_uuid:resource_class_name:resource_uuid
        return True

    async def on_channel_message(self, data: dict, websocket: WebSocket) -> None:
        json_data = self.process_cache(data['data'])
        if json_data:
            # TypeError: Message.__init__() missing 1 required positional argument:
            message = Message(**json_data)
            if message.receiver and await self.guard_resource_permitted(websocket, message.receiver):
                await websocket.send_json(asdict(message))
            # else: permission denied

    async def load_permissions(self, websocket: WebSocket) -> tuple[dict[str, Coroutine], set[str]]:
        new_channels = dict()
        existing_channels = set(self.pubsub.channels)
        async for permission_data in self.redis.scan_iter(f'permission:{websocket.user.user.uuid}'):
            permission = Permission.from_str(permission_data)
            if permission.resource_type == 'chat':
                new_channels[permission.resource_key] = partial(
                    self.on_channel_message, websocket=websocket)
                existing_channels.discard(permission.resource_key)
        new_channels['chat:3a78e770-6789-4e4a-9286-73ee6cd283a6'] = partial(
            self.on_channel_message, websocket=websocket)  # TODO remove
        return new_channels, existing_channels

    async def reload_channels(self, websocket: WebSocket, data: Any | None = None) -> None:
        add, revoke = await self.load_permissions(websocket)
        await asyncio.gather(self.pubsub.subscribe(**add), self.pubsub.unsubscribe(*revoke))

    async def pubsub_listener(self, pubsub: PubSub) -> None:
        async for data in pubsub.listen():  # type: ignore
            print('pubsub', data)

    @requires('authenticated')
    async def on_connect(self, websocket: WebSocket) -> None:
        await asyncio.gather(
            websocket.accept(),
            self.pubsub.subscribe(**{Permission.update_channel(websocket.user.user.uuid):
                                     partial(self.load_permissions, websocket=websocket)}),
            self.reload_channels(websocket),
            self.redis.set(
                name=to_redis_key(websocket.user.user),
                value=json.dumps(UserStatus.ONLINE, default=pydantic_encoder)))
        self.pubsub_task = asyncio.create_task(
            self.pubsub_listener(self.pubsub), name='pubsub_listener_task')

    async def send_message(self, message: Message, websocket: WebSocket) -> None:
        if not message.receiver:
            pass
        if not await self.guard_resource_permitted(websocket, message.receiver):
            # TODO exception or close with code ???
            pass
        message.sender = websocket.user.user
        message.uuid = uuid4()
        await self.send_message_cache(message)

    async def send_message_cache(self, message: Message) -> None:
        no_text_message = Message(
            uuid=message.uuid,
            receiver=message.receiver,
            status=message.status)
        await asyncio.gather(
            self.redis.set(
                name=to_redis_key(no_text_message),  # type: ignore
                value=json.dumps(no_text_message, default=pydantic_encoder),
                ex=CACHE_EXPIRE_TIME),
            self.redis.publish(
                channel=f'chat:{message.receiver}',
                message=json.dumps(message, default=pydantic_encoder)))

    async def update_message_cache(self, message: Message, websocket: WebSocket) -> None:
        if not (message.receiver and message.uuid):
            # TODO exception or close with code ???
            pass
        if not await self.guard_resource_permitted(websocket, message.receiver):
            # TODO exception or close with code ???
            pass
        await self.send_message_cache(message)

    def process_cache(self, cached_data: str) -> dict[str, Any]:
        json_data = {}
        try:
            json_data = json.loads(cached_data)
            if not isinstance(json_data, dict):
                # TODO exception or close with code ???
                json_data = dict()
        except json.JSONDecodeError as exception:
            # TODO cache error
            json_data = dict()
        finally:
            return json_data

    async def update_message(self, message: Message, websocket: WebSocket) -> None:
        def validate_cached_data(data: str | None) -> bool:
            if not data:
                # TODO missing cache
                return False
            if not isinstance(data, str):
                # TODO exception or close with code ???
                return False
            return True

        if not message.uuid:
            raise ValueError(
                f'Missing uuid in update message from user={websocket.user.user}')
        cached_data = await self.redis.get(name=to_redis_key(message))
        if validate_cached_data(cached_data):
            json_data = self.process_cache(cached_data)
            if json_data:
                # TypeError: Message.__init__() missing 1 required positional argument:
                cached_message = Message(**json_data)
                cached_message.status = message.status
                await self.update_message_cache(cached_message, websocket)

    async def on_websocket_message(self, message: Message, websocket: WebSocket) -> None:
        match message.status:
            case MessageStatus.SENT:
                await self.send_message(message, websocket)
            case MessageStatus.DELIVERED:
                await self.update_message(message, websocket)
            case MessageStatus.READ:
                await self.update_message(message, websocket)
            case _:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,  # TODO close codes
                    reason='Unexpected data received aaa')
                # TODO exception or close with code ???
                raise ValueError(
                    f'Incorrect MessageStatus user={websocket.user.user} message={message.uuid}, receiver={message.receiver}')

    async def on_receive(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        await self.on_websocket_message(Message(**data), websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        await self.redis.delete(to_redis_key(websocket.user.user))
        if self.pubsub_task:
            self.pubsub_task.cancel()
