import asyncio
import json
from multiprocessing.connection import wait
from random import randint
from datetime import datetime as dt
from  websockets import connect, ConnectionClosed   # type: ignore

client = randint(0, 1000)

async def main() -> None:
    waiting = dt(2022,9,12,22,50,0).timestamp() - dt.now().timestamp()
    print('waiting:', waiting)
    await asyncio.sleep(waiting)
    print('client', client)
    async for connection in connect(uri='ws://localhost:8001'):
        try:
            event = {'client': client, 'connection': randint(0,1000), 'wait': 1}
            print(event)
            await connection.send(json.dumps(event))
            print(json.loads(await connection.recv()))
        except ConnectionClosed:
            continue

if __name__ == "__main__":
    asyncio.run(main())