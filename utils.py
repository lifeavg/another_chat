import json
from pydoc import locate
from typing import Any, Iterable


def convert_json(data: str) -> dict[str, Any]:
    json_data = dict()
    try:
        json_data = json.loads(data)
        if not isinstance(json_data, dict):
            json_data = dict()
    except json.JSONDecodeError as exception:
        json_data = dict()
    finally:
        return json_data


def to_type_object(data: dict[str, Any], classes: Iterable[type]) -> Any:
    try:
        for t in classes:
            return t(**data)
    except TypeError:
        pass
    return None


def type_key(t: type) -> str:
    return t.__name__.lower()


def str_to_type(s: str) -> type:
    return locate(s.capitalize()).__class__
