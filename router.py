from starlette.routing import WebSocketRoute

from endpoints import ChatEndpoint

router = [
    WebSocketRoute(path='/', endpoint=ChatEndpoint),
]
