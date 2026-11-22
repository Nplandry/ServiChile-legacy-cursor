import threading
import time
from typing import Protocol

from app.infraestructura.redis_cliente import cliente_redis

class LimiteSolicitudes(Protocol):
    def permitir(self, clave: str, limite: int, ventana_s: int = 60) -> bool: ...

class LimiteSolicitudesRedis:
    def __init__(self, url: str) -> None:
        self._redis = cliente_redis(url)

    def permitir(self, clave: str, limite: int, ventana_s: int = 60) -> bool:
        bucket = f"rl:{clave}:{int(time.time() // ventana_s)}"
        pipe = self._redis.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, ventana_s)
        count, _ = pipe.execute()
        return int(count) <= limite

class LimiteSolicitudesMemoria:

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def permitir(self, clave: str, limite: int, ventana_s: int = 60) -> bool:
        window = int(time.time() // ventana_s)
        bucket = f"{clave}:{window}"
        with self._lock:
            self._counts = {
                k: v for k, v in self._counts.items() if k.endswith(f":{window}")
            }
            self._counts[bucket] = self._counts.get(bucket, 0) + 1
            return self._counts[bucket] <= limite

def construir_limite_solicitudes(redis_url: str | None) -> LimiteSolicitudes:
    url = (redis_url or "").strip()
    if url:
        return LimiteSolicitudesRedis(url)
    return LimiteSolicitudesMemoria()
