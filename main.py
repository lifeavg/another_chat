from json import JSONEncoder
from typing import Any
from uuid import UUID

import uvicorn
from starlette.applications import Starlette

from router import router

# https://github.com/jazzband/django-push-notifications/issues/586
default_json_encoder = JSONEncoder.default


def custom_json_encoder(self, obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    return default_json_encoder(self, obj)


JSONEncoder.default = custom_json_encoder  # type: ignore

app = Starlette(debug=True, routes=router)

# if __name__ == '__main__':
#     uvicorn.run("main:app", host='127.0.0.1', port=8005,
#                 log_level="debug", reload=True)
#     print("running")
