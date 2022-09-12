import asyncio
import json
from random import randint
from  websockets import serve  # type: ignore
from websockets.server import WebSocketServerProtocol

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
    asyncio.run(main())