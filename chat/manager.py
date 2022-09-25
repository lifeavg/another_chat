from fastapi import WebSocket
from redis import asyncio as aioredis


class SocketConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)

    async def receive_message(self, websocket: WebSocket) -> str:
        return await websocket.receive_text()

    async def broadcast(self, message: str) -> None:
        for connection in self.active_connections:
            await connection.send_text(message)


class RedisConnectionManager:
    def __init__(self) -> None:
        self.connection = aioredis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=1000,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            socket_keepalive=True)

    async def publish(self, channel: str, data: str) -> int:
        return await self.connection.publish(channel, data)
