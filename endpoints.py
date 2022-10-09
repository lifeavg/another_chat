import asyncio
import json
from dataclasses import asdict
from uuid import UUID, uuid4
from pydantic.json import pydantic_encoder
from redis.asyncio.client import PubSub, Redis
from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocket
from starlette.authentication import requires

from connections import redis as global_redis
from schemas import Message, UserStatus, MessageStatus
from utils import to_redis_key

async def check_key(key: str, redis: Redis) -> tuple[str, str | None]:
    return key, await redis.get(key)

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

    @requires('authenticated')
    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        # TODO init user permissions
        await self.pubsub.subscribe('chat:3a78e770-6789-4e4a-9286-73ee6cd283a6')
        await self.redis.set(
            name=to_redis_key(websocket.user.user),
            value=json.dumps(UserStatus.ONLINE, default=pydantic_encoder))

    async def on_receive(self, websocket: WebSocket, data: dict) -> None:
        await self._process_message(message=Message(**data), websocket=websocket)

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        await self.redis.delete(to_redis_key(websocket.user.user)) 

    async def dispatch(self) -> None:
        websocket = WebSocket(
            scope=self.scope, receive=self.receive, send=self.send)
        await self.on_connect(websocket=websocket)
        if websocket.user.is_authenticated:
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
        else:
            raise ValueError(
                f'Unexpected value \'type \'={message["type"]} in websocket={websocket}')

    async def _dispatch_pubsub(self, websocket: WebSocket, timeout: float = 0.0) -> None:
        if self.pubsub.subscribed:
            raw_data = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if raw_data:
                await self._on_receive_pubsub(raw_data=raw_data['data'], websocket=websocket)
        else:
            await asyncio.sleep(timeout)

    async def _on_receive_pubsub(self, raw_data: str, websocket: WebSocket) -> None:
        if not raw_data:
            return None # TODO missing cache
        if not isinstance(raw_data, str):
            raise ValueError(f'Incorrect data str in cache for message user={websocket.user.user}') # TODO exception or close with code ???
        try:
            json_data = json.loads(raw_data)
            if not isinstance(json_data, dict):
                raise ValueError(f'Incorrect data dict in cache for message user={websocket.user.user}') # TODO exception or close with code ???
        except json.JSONDecodeError as exception:
            # TODO cache error
            pass
        else:
            message_data = Message(**json_data) # TypeError: Message.__init__() missing 1 required positional argument:
            await websocket.send_json(asdict(message_data))

    async def _guard_chat_permitted(self, websocket: WebSocket, receiver: UUID) -> bool:
        # permission:user_uuid:resource_class_name:resource_uuid
        return True

    async def _sent_message(self, message: Message, websocket: WebSocket) -> None:
        if not message.receiver:
            raise ValueError(f'Missing receiver in message from user={websocket.user.user}')
        if not await self._guard_chat_permitted(websocket, message.receiver):
            raise ValueError(f'Access denied for user={websocket.user.user} to {message.receiver}') # TODO exception or close with code ???
        message.sender = websocket.user.user
        message.uuid = uuid4()
        no_text_message = Message(uuid=message.uuid, receiver=message.receiver, status=message.status)
        await self.redis.set(
            name=to_redis_key(no_text_message),  # type: ignore
            value=json.dumps(no_text_message, default=pydantic_encoder))
        await self.redis.publish(
            channel=f'chat:{message.receiver}',
            message=json.dumps(message, default=pydantic_encoder))

    async def _update_message(self, message: Message, websocket: WebSocket) -> None:
        if not message.uuid:
            raise ValueError(f'Missing uuid in update message from user={websocket.user.user}')
        cached_data = await self.redis.get(name=to_redis_key(message))  # type: ignore
        if not cached_data:
            return None # TODO missing cache
        if not isinstance(cached_data, str):
            raise ValueError(f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}') # TODO exception or close with code ???
        try:
            json_data = json.loads(cached_data)
            if not isinstance(json_data, dict):
                raise ValueError(f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}') # TODO exception or close with code ???
        except json.JSONDecodeError as exception:
            # TODO cache error
            pass
        else:
            cached_message = Message(**json_data) # TypeError: Message.__init__() missing 1 required positional argument:
            if not (cached_message.receiver and cached_message.uuid):
                raise ValueError(f'Incorrect data in cache for message {message.uuid} user={websocket.user.user}') # TODO exception or close with code ???
            if not await self._guard_chat_permitted(websocket, cached_message.receiver):
                raise ValueError(f'Access denied for user={websocket.user.user} to {message.receiver}') # TODO exception or close with code ???
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
            case _ :
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION, # TODO close codes
                    reason='Unexpected data received aaa')
                raise ValueError(f'Incorrect MessageStatus user={websocket.user.user} message={message.uuid}, receiver={message.receiver}') # TODO exception or close with code ???

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
