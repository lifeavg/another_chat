from schemas import HasUUID, Message, MessageConfirmation, Subscription


def to_redis_key(object: HasUUID) -> str:
    return f'{object.__class__.__name__.lower()}:{object.uuid}'


def from_json(json_data: dict) -> Message | Subscription | MessageConfirmation | None:
    types = [Message, Subscription, MessageConfirmation]
    for t in types:
        try:
            return t(**json_data)
        except TypeError as exception:
            pass
