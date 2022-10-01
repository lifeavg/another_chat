import uvicorn
import json
import asyncio
from dataclasses import asdict
from json import JSONEncoder
from typing import Any
from uuid import UUID, uuid4

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.types import Receive, Scope, Send
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket
from redis import asyncio as aioredis
from redis.asyncio.client import PubSub, Redis

from schemas import *

# https://github.com/jazzband/django-push-notifications/issues/586
def custom_json_encoder(self, obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    return default_json_encoder(self, obj)

default_json_encoder = JSONEncoder.default
JSONEncoder.default = custom_json_encoder  # type: ignore


def to_redis_key(object: HasUUID) -> str:
    return f'{object.__class__.__name__.lower()}:{object.uuid}'

def from_json(json_data: dict) -> Message | Subscription | MessageConfirmation | None:
    types = [Message, Subscription, MessageConfirmation]
    for t in types:
        try:
            return t(**json_data)
        except TypeError as exception:
            pass

redis = aioredis.from_url(
    "redis://localhost:6379",
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=1000,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    socket_keepalive=True)

class ChatConnection(WebSocketEndpoint):
    encoding = 'json'
    
    def __init__(self,
                 scope: Scope,
                 receive: Receive,
                 send: Send,
                 redis: Redis = redis) -> None:
        super().__init__(scope, receive, send)
        self.redis: Redis = redis
        self.subscriptions: set[Chat] = set()
        self.pubsub: PubSub = redis.pubsub()
        self.user: User | None = None
        self.websocket: WebSocket | None = None
        self.pending_tasks: set[asyncio.Task] = set()

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.websocket = websocket

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        o_data = from_json(data)
        match o_data:
            case Message():
                o_data.uuid = uuid4()
                o_data.sender = self.user
                await redis.publish(to_redis_key(o_data.receiver), json.dumps(asdict(o_data)))
            case Subscription():
                if o_data.subscribe:
                    if not self.user:
                        self.user = o_data.user
                    new_subscriptions = set(o_data.chats) - self.subscriptions
                    if new_subscriptions:
                        self.subscriptions |= new_subscriptions
                        await self.pubsub.subscribe(*[to_redis_key(x) for x in new_subscriptions])
                else:
                    self.subscriptions -= set(o_data.chats)
                    await self.pubsub.unsubscribe(*[to_redis_key(x) for x in o_data.chats])
            case MessageConfirmation():
                pass
            case _:
                await websocket.send_json(asdict(o_data))

    async def on_disconnect(self, websocket, close_code):
        print(close_code, 'disconnect', websocket)

    async def dispatch(self) -> None:
        if not self.pending_tasks:
            self.pending_tasks.add(asyncio.create_task(super().dispatch(), name='socket_connection'))
            self.pending_tasks.add(asyncio.create_task(self.dispatch_redis_sub(), name='redis_subscription'))
        while self.pending_tasks:
            done, self.pending_tasks = await asyncio.wait(self.pending_tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                await task
                match task.get_name():
                    case 'socket_connection':
                        self.pending_tasks.add(asyncio.create_task(super().dispatch(), name='socket_connection'))
                    case 'redis_subscription':
                        self.pending_tasks.add(asyncio.create_task(self.dispatch_redis_sub(), name='redis_subscription'))
                    case _:
                        pass
            await asyncio.sleep(1)

    async def dispatch_redis_sub(self) -> None:
        while self.pubsub.subscribed:
            raw_data = await self.pubsub.get_message(ignore_subscribe_messages=True)
            if raw_data and self.websocket:
                data = from_json(json.loads(raw_data['data']))
                match data:
                    case Message():
                        await self.websocket.send_json(asdict(data))
                    case _:
                        pass


app = Starlette(debug=True, routes=[
    WebSocketRoute(path='/', endpoint=ChatConnection),
])

# if __name__ == '__main__':
#     uvicorn.run("main:app", host='127.0.0.1', port=8005,
#                 log_level="debug", reload=True)
#     print("running")
