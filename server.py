from __future__ import annotations
import asyncio
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from enum import Enum, auto
import json
from random import randint
from collections.abc import Iterable
from  websockets import serve  # type: ignore
from websockets.server import WebSocketServerProtocol
import uuid
from datetime import datetime

class MessageState(Enum):
    SENT = 'SENT'
    DELIVERED = 'DELIVERED' 
    READ = 'READ'

@dataclass
class User:
    id: uuid.UUID
    name: str

@dataclass
class Chat:
    id: uuid.UUID
    name: str
    created: datetime
    users: Iterable[User]
    messages: Iterable[Message]

@dataclass
class Message:
    id: uuid.UUID
    sender: User
    text: str
    chat: uuid.UUID
    state: MessageState
    timestamp: datetime
    
async def handler(websocket: WebSocketServerProtocol):
    async for message in websocket:
        event = json.loads(message)
        print('received: ', event)
        await asyncio.sleep(event['wait'])
        await websocket.send(json.dumps(event))
        print('responded: ', event)

async def main() -> None:
    async with serve(
        ws_handler=handler,
        host="", port=8001):
        await asyncio.Future()

if __name__ == "__main__":
    # asyncio.run(main())
    u = {'id':uuid.uuid4(), 'sender': {'id':uuid.uuid4(),'name':'uusseeerrr'}, 'text':'aaAAAaaAAA', 'chat':uuid.uuid4(), 'state':MessageState.SENT, 'timestamp': datetime.now()}
    print('dict', u)
    du = Message(**u)
    print('message', du)
    ju = json.dumps(du, default=pydantic_encoder)
    print('string', ju)
    lu = json.loads(ju)
    print('loaded dict', lu)
    print('loaded message', Message(**lu))
