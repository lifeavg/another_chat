import asyncio
import json
from dataclasses import asdict
from uuid import UUID, uuid4

from redis.asyncio.client import PubSub, Redis
from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket
from starlette.authentication import requires

from connections import redis as global_redis
from schemas import (Message, MessageConfirmation, Subscription, User,
                     AccessUserPermissions, UserType, Chat, UserRole)
from utils import from_json, to_redis_key

async def process_message(message: Message, redis: Redis) -> None:
    await redis.publish(channel=to_redis_key(object=message.receiver), message=json.dumps(asdict(message)))


async def process_subscription(subscription: Subscription, pubsub: PubSub) -> None:
    existing_channels = set(pubsub.channels.keys())
    received_channels = set(to_redis_key(object=x) for x in subscription.chats)
    if subscription.subscribe:
        new_channels = received_channels - existing_channels
        if new_channels:
            await pubsub.subscribe(*new_channels)
    else:
        await pubsub.unsubscribe(*received_channels)

# def authenticate(token: str) -> AccessUserPermissions | None:
#     # return AccessUserPermissions(user=User(uuid=UUID('3b4827ad-32cc-49ef-9e8a-7abdfe196ef2'), name='userOne'), user_type=UserType.USER, chats={Chat(uuid=UUID('3a78e770-6789-4e4a-9286-73ee6cd283a6'), name='chatOne'):UserRole.POSTER, Chat(uuid=UUID('4ec6b6b5-f32f-4b01-80c9-80e51fdc65ee'), name='chatTwo'):UserRole.POSTER})
#     return None

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
        self.access: AccessUserPermissions | None = None

    @requires('authenticated')
    async def on_connect(self, websocket: WebSocket) -> None:
        print(websocket.user)
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        o_data = from_json(data)
        match o_data:
            case Message():
                await self._process_message(message=o_data, websocket=websocket)
            case Subscription():
                await process_subscription(subscription=o_data, pubsub=self.pubsub)
            case MessageConfirmation():
                pass
            case _:
                raise TypeError(f'Unexpected data type {o_data.__class__.__name__}'
                                f'received from websocket {websocket}')

    # async def on_disconnect(self, websocket: WebSocket, close_code: int):
    #     pass

    async def dispatch(self) -> None:
        websocket = WebSocket(
            scope=self.scope, receive=self.receive, send=self.send)
        await self.on_connect(websocket=websocket)

        close_code = status.WS_1000_NORMAL_CLOSURE
        pending_tasks: set[asyncio.Task] = set()
        pending_tasks.add(asyncio.create_task(
            coro=self._dispatch_websocket(websocket=websocket), name='socket_connection'))
        pending_tasks.add(asyncio.create_task(
            coro=self._dispatch_pubsub(websocket=websocket, timeout=5), name='redis_subscription'))
        try:
            while True:
                done, pending_tasks = await asyncio.wait(
                    fs=pending_tasks,
                    return_when=asyncio.FIRST_COMPLETED)
                result = await self._process_dispatch_results(
                    tasks=done,
                    pending_tasks=pending_tasks,
                    websocket=websocket)
                if result:
                    close_code = result
                    break
        except Exception as exception:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exception
        finally:
            for task in pending_tasks:
                task.cancel()
            await self.on_disconnect(websocket=websocket, close_code=close_code)

    async def _dispatch_websocket(self, websocket: WebSocket) -> None | int:
        message = await websocket.receive()
        if message['type'] == 'websocket.receive':
            data = await self.decode(websocket, message)
            await self.on_receive(websocket=websocket, data=data)
        elif message['type'] == 'websocket.disconnect':
            return int(message.get("code") or status.WS_1000_NORMAL_CLOSURE)
        # else:
        #     raise ValueError(
        #         f'Unexpected value \'type \'={message["type"]} in websocket={websocket}')

    async def _dispatch_pubsub(self, websocket: WebSocket, timeout: float = 0.0) -> None:
        if self.pubsub.subscribed:
            raw_data = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if raw_data:
                await self._on_receive_pubsub(raw_data=raw_data['data'], websocket=websocket)
        else:
            await asyncio.sleep(timeout)

    async def _on_receive_pubsub(self, raw_data: str, websocket: WebSocket) -> None:
        data = from_json(json_data=json.loads(raw_data))
        match data:
            case Message():
                await websocket.send_json(asdict(data))
            case _:
                raise TypeError(f'Unexpected data type {data.__class__.__name__}'
                                'received from pubsub channel')

    async def _process_message(self, message: Message, websocket: WebSocket) -> None:
        if not self.access:
            return None
        message.sender = self.access.user
        message.uuid = uuid4()
        await process_message(message=message, redis=self.redis)

    async def _process_dispatch_results(
            self,
            tasks: set[asyncio.Task],
            pending_tasks: set[asyncio.Task],
            websocket: WebSocket) -> int | None:
        for task in tasks:
            result = await task
            task_name = task.get_name()
            if task_name == 'socket_connection' and result:
                return result
            elif task_name == 'socket_connection' and not result:
                pending_tasks.add(asyncio.create_task(
                    coro=self._dispatch_websocket(websocket), name='socket_connection'))
            elif task_name == 'redis_subscription':
                pending_tasks.add(asyncio.create_task(
                    coro=self._dispatch_pubsub(websocket, 5), name='redis_subscription'))
            else:
                raise ValueError(
                    f'Unexpected task result={result} task_name={task_name}')
