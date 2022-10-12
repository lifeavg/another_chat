import asyncio
import json
from dataclasses import asdict
from functools import partial
from typing import Coroutine
from uuid import UUID, uuid4

from pydantic.json import pydantic_encoder
from redis.asyncio.client import PubSub, Redis
from starlette import status
from starlette.authentication import requires
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket

from connections import redis as global_redis
from schemas import Message, MessageStatus, UserStatus
from utils import to_redis_key


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

    async def on_message(self, data: dict, websocket: WebSocket) -> None:
        try:
            json_data = json.loads(data['data'])
            if not isinstance(json_data, dict):
                # TODO exception or close with code ???
                raise ValueError(
                    f'Incorrect data dict in cache for message user={websocket.user.user}')
        except json.JSONDecodeError as exception:
            # TODO cache error
            pass
        else:
            # TypeError: Message.__init__() missing 1 required positional argument:
            message_data = Message(**json_data)
            await websocket.send_json(asdict(message_data))

    async def load_permissions(self, websocket: WebSocket) -> dict[str, Coroutine]:
        subs = dict()
        async for key in self.redis.scan_iter(f'permission:{websocket.user.user.uuid}'):
            resource = key.split(':')
            if resource[1] == 'chat':
                subs[f'{resource[1]}:{resource[2]}'] = partial(
                    self.on_message, websocket=websocket)
        subs['chat:3a78e770-6789-4e4a-9286-73ee6cd283a6'] = partial(
            self.on_message, websocket=websocket)
        return subs

    async def pubsub_listener(self, pubsub: PubSub) -> None:
        async for data in pubsub.listen():  # type: ignore
            print('pubsub', data)

    @requires('authenticated')
    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        # init user permissions
        await self.pubsub.subscribe(f'permission:update:{websocket.user.user.uuid}')
        await self.pubsub.subscribe(**await self.load_permissions(websocket))
        await self.redis.set(
            name=to_redis_key(websocket.user.user),
            value=json.dumps(UserStatus.ONLINE, default=pydantic_encoder))
        self.pubsub_task = asyncio.create_task(
            self.pubsub_listener(self.pubsub), name='pubsub_listener_task')

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        await self._process_message(message=Message(**data), websocket=websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        await self.redis.delete(to_redis_key(websocket.user.user))
        if self.pubsub_task:
            self.pubsub_task.cancel()

    async def _guard_chat_permitted(self, websocket: WebSocket, receiver: UUID) -> bool:
        # permission:user_uuid:resource_class_name:resource_uuid
        return True

    async def _sent_message(self, message: Message, websocket: WebSocket) -> None:
        if not message.receiver:
            raise ValueError(
                f'Missing receiver in message from user={websocket.user.user}')
        if not await self._guard_chat_permitted(websocket, message.receiver):
            # TODO exception or close with code ???
            raise ValueError(
                f'Access denied for user={websocket.user.user} to {message.receiver}')
        message.sender = websocket.user.user
        message.uuid = uuid4()
        no_text_message = Message(
            uuid=message.uuid, receiver=message.receiver, status=message.status)
        await self.redis.set(
            name=to_redis_key(no_text_message),  # type: ignore
            value=json.dumps(no_text_message, default=pydantic_encoder))
        await self.redis.publish(
            channel=f'chat:{message.receiver}',
            message=json.dumps(message, default=pydantic_encoder))

    async def _update_message(self, message: Message, websocket: WebSocket) -> None:
        if not message.uuid:
            raise ValueError(
                f'Missing uuid in update message from user={websocket.user.user}')
        cached_data = await self.redis.get(name=to_redis_key(message)) # type: ignore
        if not cached_data:
            return None  # TODO missing cache
        if not isinstance(cached_data, str):
            # TODO exception or close with code ???
            raise ValueError(
                f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}')
        try:
            json_data = json.loads(cached_data)
            if not isinstance(json_data, dict):
                # TODO exception or close with code ???
                raise ValueError(
                    f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}')
        except json.JSONDecodeError as exception:
            # TODO cache error
            pass
        else:
            # TypeError: Message.__init__() missing 1 required positional argument:
            cached_message = Message(**json_data)
            if not (cached_message.receiver and cached_message.uuid):
                # TODO exception or close with code ???
                raise ValueError(
                    f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}')
            if not await self._guard_chat_permitted(websocket, cached_message.receiver):
                # TODO exception or close with code ???
                raise ValueError(
                    f'Access denied for user={websocket.user.user} to {message.receiver}')
            cached_message.status = message.status
            await self.redis.set(
                name=to_redis_key(cached_message),  # type: ignore
                value=json.dumps(cached_message, default=pydantic_encoder))
            await self.redis.publish(
                channel=f'chat:{cached_message.receiver}',
                message=json.dumps(cached_message, default=pydantic_encoder))

    async def _process_message(self, message: Message, websocket: WebSocket) -> None:
        match message.status:
            case MessageStatus.SENT:
                await self._sent_message(message=message, websocket=websocket)
            case MessageStatus.DELIVERED:
                await self._update_message(message=message, websocket=websocket)
            case MessageStatus.READ:
                await self._update_message(message=message, websocket=websocket)
            case _:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,  # TODO close codes
                    reason='Unexpected data received aaa')
                # TODO exception or close with code ???
                raise ValueError(
                    f'Incorrect MessageStatus user={websocket.user.user} message={message.uuid}, receiver={message.receiver}')
