from redis import asyncio as aioredis

redis = aioredis.from_url(
    "redis://redis:6379",
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=1000,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    socket_keepalive=True)
