from starlette.routing import WebSocketRoute

from endpoints import ChatConnection

router = [
    WebSocketRoute(path='/', endpoint=ChatConnection),
]
