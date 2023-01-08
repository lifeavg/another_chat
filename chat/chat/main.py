from json import JSONEncoder
from typing import Any
from uuid import UUID


from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from chat.authentication import AuthenticationManager
from chat.schemas import MessageStatus


from chat.router import router

# # https://github.com/jazzband/django-push-notifications/issues/586
default_json_encoder = JSONEncoder.default


def custom_json_encoder(self, obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, MessageStatus):
        return obj.value
    return default_json_encoder(self, obj)


JSONEncoder.default = custom_json_encoder  # type: ignore


middleware = [
    Middleware(AuthenticationMiddleware, backend=AuthenticationManager())
]

app = Starlette(debug=True, routes=router, middleware=middleware)
