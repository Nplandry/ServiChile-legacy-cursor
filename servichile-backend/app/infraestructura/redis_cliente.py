

from __future__ import annotations

from functools import lru_cache
from typing import Any

@lru_cache
def cliente_redis(url: str) -> Any:

    import redis

    limpia = (url or "").strip()
    if not limpia:
        raise ValueError("REDIS_URL vacío.")
    return redis.Redis.from_url(
        limpia,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
        retry_on_timeout=True,
    )

def ping_redis(url: str) -> None:
    client = cliente_redis(url.strip())
    if client.ping() is not True:
        raise RuntimeError("Redis PING no devolvió True.")
