import asyncio
import json
from dataclasses import asdict
from json import JSONEncoder
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis
from redis.asyncio.client import PubSub, Redis

from .schemas import *

default_json_encoder = JSONEncoder.default


def custom_json_encoder(self, obj: Any):
    if isinstance(obj, UUID):
        return str(obj)
    return default_json_encoder(self, obj)


JSONEncoder.default = custom_json_encoder  # type: ignore

router = APIRouter(prefix="/chat", tags=["chat"])
redis = aioredis.from_url(
    "redis://localhost:6379",
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=1000,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    socket_keepalive=True)


def from_json(json_data: dict) -> Message | Subscription | Confirmation | None:
    types = [Message, Subscription, Confirmation]
    for t in types:
        try:
            return t(**json_data)
        except TypeError as exception:
            pass


async def receive_data(websocket: WebSocket) -> Message | Subscription | Confirmation | None:
    raw_data = None
    try:
        raw_data = await websocket.receive_text()
    except WebSocketDisconnect as exception:
        pass
    json_data = None
    if raw_data:
        try:
            json_data = json.loads(raw_data)
        except json.JSONDecodeError:
            pass
    if json_data:
        return from_json(json_data)


def to_redis_key(object: HasUUID) -> str:
    return f'{object.__class__.__name__.lower()}:{object.uuid}'


async def socket_connection(
        websocket: WebSocket,
        redis: Redis,
        user: User,
        pubsub: PubSub,
        subscriptions: set[Chat]) -> str:
    while True:
        data = await receive_data(websocket)
        match data:
            case Message():
                data.uuid = uuid4()
                data.sender = user
                await redis.publish(to_redis_key(data.receiver), json.dumps(asdict(data)))
                break
            case Subscription():
                new_subscriptions = set(data.chats) - subscriptions
                if new_subscriptions:
                    await pubsub.subscribe(*[to_redis_key(x) for x in new_subscriptions])
                    subscriptions |= new_subscriptions
                break
            case Confirmation():
                break
            case _:
                break
    return 'socket_connection'


async def redis_subscription(
        websocket: WebSocket,
        pubsub: PubSub) -> str:
    while True:
        raw_data = await pubsub.get_message(ignore_subscribe_messages=True)
        if raw_data:
            data = from_json(json.loads(raw_data['data']))
            match data:
                case Message():
                    await websocket.send_text(raw_data['data'])
                    break
                case _:
                    break
    return 'redis_subscription'


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    init_subscription = await receive_data(websocket)
    if not init_subscription or not isinstance(init_subscription, Subscription) or not init_subscription.subscribe:
        raise ValueError('Expected initialize message')
    pubsub = redis.pubsub()
    subscriptions: set[Chat] = set(init_subscription.chats)
    await pubsub.subscribe(*[to_redis_key(x) for x in subscriptions])
    pending = {asyncio.create_task(socket_connection(websocket, redis, init_subscription.user, pubsub, subscriptions)),
               asyncio.create_task(redis_subscription(websocket, pubsub))}
    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = await task
            match result:
                case 'socket_connection':
                    pending.add(asyncio.create_task(socket_connection(
                        websocket, redis, init_subscription.user, pubsub, subscriptions)))
                case 'redis_subscription':
                    pending.add(asyncio.create_task(redis_subscription(
                        websocket, pubsub)))
                case _:
                    break
