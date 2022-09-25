import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as ar
from redis.asyncio.client import PubSub

from .manager import RedisConnectionManager, SocketConnectionManager

router = APIRouter(prefix="/chat", tags=["chat"])
socket_manager = SocketConnectionManager()
redis_manager = RedisConnectionManager()


async def socket_connection(
        new_websocket: WebSocket,
        socket_manager: SocketConnectionManager,
        redis_manager: RedisConnectionManager) -> str:
    try:
        while True:
            data = await socket_manager.receive_message(new_websocket)
            if data:
                parsed = data.split(' ')
                await redis_manager.publish(parsed[0], parsed[1])
                return 'socket_connection'
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await socket_manager.disconnect(new_websocket)
        return 'socket_connection'


async def redis_subscription(
        new_websocket: WebSocket,
        channel: str,
        socket_manager: SocketConnectionManager,
        redis_manager: RedisConnectionManager) -> str:
    pubsub = redis_manager.connection.pubsub()
    await pubsub.subscribe(channel)
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            await socket_manager.send_message(str(message), new_websocket)
            return 'redis_subscription'
        await asyncio.sleep(1)


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    await socket_manager.connect(websocket)
    data = [None, None]
    parsed = []
    try:
        data = await socket_manager.receive_message(websocket)
        if data:
            parsed = data.split(' ')
            # no consumer - data lost
            # await redis_manager.publish(parsed[0], parsed[1])
    except WebSocketDisconnect:
        await socket_manager.disconnect(websocket)
    pending = {asyncio.create_task(socket_connection(websocket, socket_manager, redis_manager)),
               asyncio.create_task(redis_subscription(websocket, str(parsed[0]), socket_manager, redis_manager))}
    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            print(len(pending))
            result = await task
            match result:
                case 'socket_connection':
                    pending.add(asyncio.create_task(socket_connection(
                        websocket, socket_manager, redis_manager)))
                case 'redis_subscription':
                    pending.add(asyncio.create_task(redis_subscription(
                        websocket, str(parsed[0]), socket_manager, redis_manager)))
                case _:
                    break
