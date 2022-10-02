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
from schemas import Message, MessageConfirmation, Subscription, User
from utils import from_json, to_redis_key


class ChatConnection(WebSocketEndpoint):
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
                o_data.uuid = uuid4()
                o_data.sender = self.user
                await self.redis.publish(to_redis_key(o_data.receiver), json.dumps(asdict(o_data)))
            case Subscription():
                existing_channels = set(self.pubsub.channels.keys())
                received_channels = set(to_redis_key(x) for x in o_data.chats)
                if o_data.subscribe:
                    if not self.user:
                        self.user = o_data.user
                    new_channels = received_channels - existing_channels
                    if new_channels:
                        await self.pubsub.subscribe(*new_channels)
                else:
                    await self.pubsub.unsubscribe(*received_channels)
            case MessageConfirmation():
                pass
            case _:
                await websocket.send_json(asdict(o_data))

    # async def on_disconnect(self, websocket, close_code):
    #     pass

    async def process_result(self, tasks: set[asyncio.Task], pending_tasks: set[asyncio.Task], websocket: WebSocket) -> int | None:
        for task in tasks:
            result = await task
            if task.get_name() == 'socket_connection' and result:
                return result
            elif task.get_name() == 'socket_connection' and not result:
                pending_tasks.add(asyncio.create_task(
                    self.dispatch_websocket(websocket), name='socket_connection'))
            elif task.get_name() == 'redis_subscription':
                pending_tasks.add(asyncio.create_task(
                    self.dispatch_redis_sub(websocket, 5), name='redis_subscription'))
            else:
                pass

    async def dispatch(self) -> None:
        websocket = WebSocket(self.scope, receive=self.receive, send=self.send)
        await self.on_connect(websocket)
        close_code = status.WS_1000_NORMAL_CLOSURE
        pending_tasks: set[asyncio.Task] = set()
        pending_tasks.add(asyncio.create_task(
            self.dispatch_websocket(websocket), name='socket_connection'))
        pending_tasks.add(asyncio.create_task(
            self.dispatch_redis_sub(websocket, 5), name='redis_subscription'))
        try:
            while True:
                done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
                result = await self.process_result(done, pending_tasks, websocket)
                if result:
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc
        finally:
            for task in pending_tasks:
                task.cancel()
            await self.on_disconnect(websocket, close_code)

    async def dispatch_websocket(self, websocket: WebSocket) -> int | None:
        message = await websocket.receive()
        if message["type"] == "websocket.receive":
            data = await self.decode(websocket, message)
            await self.on_receive(websocket, data)
        elif message["type"] == "websocket.disconnect":
            return int(message.get("code") or status.WS_1000_NORMAL_CLOSURE)

    async def dispatch_redis_sub(self, websocket: WebSocket, timeout: float = 0.0) -> None:
        if self.pubsub.subscribed:
            raw_data = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if raw_data and websocket:
                data = from_json(json.loads(raw_data['data']))
                match data:
                    case Message():
                        await websocket.send_json(asdict(data))
                    case _:
                        pass
        else:
            await asyncio.sleep(timeout)
