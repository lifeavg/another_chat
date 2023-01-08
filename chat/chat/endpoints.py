import asyncio
import json
from functools import partial
from typing import Any, Callable
from uuid import UUID

from pydantic.json import pydantic_encoder
from redis.asyncio.client import PubSub, Redis
from starlette.authentication import requires
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from chat.authentication import RoleManager, AuthUser
from chat.connections import redis as redis_connection
from chat.schemas import (Chat, Message, UserStatus)
from chat.utils import convert_json, type_key

CACHE_EXPIRE_TIME = 18000  # 5h


class RedisChatEndpoint:

    def __init__(self, redis: Redis) -> None:
        self.redis: Redis = redis
        self.pubsub: PubSub = self.redis.pubsub()
        self.pubsub_listener: asyncio.Task | None = None

    async def listen(self) -> None:
        async for data in self.pubsub.listen():  # type: ignore
            print('unexpected data in listener', data)

    def start_listener(self) -> None:
        self.pubsub_listener = asyncio.create_task(
            self.listen(), name=f'pubsub_listener_task_{self.pubsub}')

    def stop_listener(self) -> None:
        if self.pubsub_listener:
            self.pubsub_listener.cancel()

    async def reset_channels(self,
                             add: set[str],
                             revoke: set[str],
                             callback: Callable) -> None:
        tasks = set()
        if add:
            tasks.add(self.pubsub.subscribe(**dict((x, callback) for x in add)))
        if revoke:
            tasks.add(self.pubsub.unsubscribe(*revoke))
        await asyncio.gather(*tasks)

    # async def set_message(self, message: CachedMessage, expr_time: float) -> None:
    #     await self.redis.set(
    #         name=message.redis_key,
    #         value=json.dumps(message, default=pydantic_encoder),
    #         ex=expr_time)

    # async def get_message(self, message_uuid: UUID, class_name: type = CachedMessage) -> CachedMessage | None:
    #     cached_data = await self.redis.get(f'{type_key(class_name)}:{message_uuid}')
    #     if cached_data:
    #         json_data = convert_json(cached_data)
    #         if json_data:
    #             try:
    #                 return CachedMessage(**json_data)
    #             except TypeError as exception:
    #                 return None
    #     return None

    # async def publish_message(self, message: Message, channel_type: type = Chat) -> int:
    #     return await self.redis.publish(
    #         channel=f'{type_key(channel_type)}:{message.receiver}',
    #         message=json.dumps(message, default=pydantic_encoder))

    # async def publish_message_update(self, message: UpdateMessage, receiver: UUID, channel_type: type = Chat) -> int:
    #     return await self.redis.publish(
    #         channel=f'{type_key(channel_type)}:{receiver}',
    #         message=json.dumps(message, default=pydantic_encoder))

    # async def cache_message(self, message: Message, expr_time: float) -> None:
    #     await asyncio.gather(self.set_message(CachedMessage(receiver=message.receiver,
    #                                                         status=message.status,
    #                                                         sender=message.sender,
    #                                                         uuid=message.uuid),
    #                                           expr_time),
    #                          self.publish_message(message))

    # async def cache_message_update(self, message: CachedMessage, expr_time: float) -> None:
    #     await asyncio.gather(
    #         self.set_message(message, expr_time),
    #         self.publish_message_update(
    #             UpdateMessage(
    #                 status=message.status,
    #                 uuid=message.uuid),
    #                 message.receiver))


class ChatEndpoint(WebSocketEndpoint):
    encoding = 'json'

    @requires('authenticated')
    async def on_connect(self, websocket: WebSocket) -> None:
        self.redis = RedisChatEndpoint(redis_connection)
        self.roles = RoleManager(redis_connection, websocket.user.chat_user)
        on_sub_callback = partial(
            self.on_sub,
            websocket=websocket)
        _, _, resources = await asyncio.gather(
            websocket.accept(),
            self.redis.redis.set(
                name=websocket.user.chat_user.redis_key,
                value=json.dumps(UserStatus.ONLINE, default=pydantic_encoder)),
            self.roles.reload_cache())
        self.redis.start_listener()

    async def on_receive(self, websocket: WebSocket, data: dict[str, Any]) -> None:
        pass
    #     obj = to_type_object(data, (NewMessage, UpdateMessage))
    #     match obj:
    #         case NewMessage():
    #             if await self.security.is_permitted(Permission(user_uuid=websocket.user.uuid,
    #                                                            resource_type=Chat,
    #                                                            resource_uuid=obj.receiver)):
    #                 await self.redis.cache_message(Message(receiver=obj.receiver,
    #                                                        status=MessageStatus.SENT,
    #                                                        sender=websocket.user.user,
    #                                                        text=obj.text,
    #                                                        uuid=uuid4()),
    #                                                CACHE_EXPIRE_TIME)
    #         case UpdateMessage():
    #             cached = await self.redis.get_message(obj.uuid)
    #             if cached and await self.security.is_permitted(Permission(user_uuid=cached.sender.uuid,
    #                                                                       resource_type=Chat,
    #                                                                       resource_uuid=cached.receiver)):
    #                 await self.redis.cache_message_update(CachedMessage(receiver=cached.receiver,
    #                                                                     status=obj.status,
    #                                                                     sender=cached.sender,
    #                                                                     uuid=cached.uuid),
    #                                                       CACHE_EXPIRE_TIME)
    #         case _:
    #             pass

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        if isinstance(websocket.user, AuthUser):
            await self.redis.redis.delete(websocket.user.chat_user.redis_key)
            await self.roles.clear_cache()
        self.redis.stop_listener()

    async def on_sub(self, channel_data: dict[str, Any], websocket: WebSocket) -> None:
        pass
        # data = channel_data.get('data')
        # if data:
        #     obj = to_type_object(convert_json(str(data)),
        #                          (Message, UpdateMessage))
        #     match obj:
        #         case Message():
        #             if await self.roles.role(Chat(uuid=obj.receiver)) >= RoleLevel.WRITER:
        #                 await websocket.send_json(asdict(obj))
        #         case UpdateMessage():
        #             cached = await self.redis.get_message(obj.uuid)
        #             if await self.roles.role(Chat(uuid=obj.receiver)) >= RoleLevel.WRITER:

        #                 await websocket.send_json(asdict(obj))
        #         case _:
        #             pass
