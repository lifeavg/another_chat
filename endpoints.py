import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from redis.asyncio.client import PubSub, Redis
from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket

from connections import redis as global_redis
from schemas import (Message, MessageConfirmation, Subscription, User,
                     UserStatus)
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
        self.user: User | None = None

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        o_data = from_json(data)
        match o_data:
            case Message():
                await self._process_message(message=o_data)
            case Subscription():
                # TODO authorization and authentication on_connect
                if not self.user:
                    self.user = o_data.user
                    await self.redis.set(name=to_redis_key(object=self.user), value=str(UserStatus.ONLINE))
                await process_subscription(subscription=o_data, pubsub=self.pubsub)
            case MessageConfirmation():
                pass
            case _:
                # exception incorrect data received
                pass

    # async def on_disconnect(self, websocket, close_code):
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
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc
        finally:
            for task in pending_tasks:
                task.cancel()
            await self.on_disconnect(websocket=websocket, close_code=close_code)

    async def _dispatch_websocket(self, websocket: WebSocket) -> int | None:
        message = await websocket.receive_json()
        if message['type'] == 'websocket.receive':
            await self.on_receive(websocket=websocket, data=message['data'])
        elif message['type'] == 'websocket.disconnect':
            return int(message.get("code") or status.WS_1000_NORMAL_CLOSURE)
        else:
            # unexpected message type
            pass

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
                # unexpected message type
                pass

    async def _process_message(self, message: Message) -> None:
        if not self.user:
            pass  # exception unauthorized
        message.sender = self.user
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
                # unexpected job results exception
                pass
