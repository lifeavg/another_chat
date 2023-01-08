from starlette.routing import WebSocketRoute

from chat.endpoints import ChatEndpoint

router = [
    WebSocketRoute(path='/', endpoint=ChatEndpoint),
]
