

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from app.infraestructura.redis_cliente import cliente_redis

PREF_MAPA = "sc:mapa:v1:"
PREF_REP = "sc:rep:v1:"

class CacheRespuesta(Protocol):
    def obtener_json(self, clave: str) -> Any | None: ...

    def guardar_json(self, clave: str, valor: Any, ttl_s: int) -> None: ...

    def borrar(self, clave: str) -> None: ...

    def borrar_prefijo(self, prefijo: str) -> None: ...

class CacheNulo:
    def obtener_json(self, clave: str) -> Any | None:
        return None

    def guardar_json(self, clave: str, valor: Any, ttl_s: int) -> None:
        return None

    def borrar(self, clave: str) -> None:
        return None

    def borrar_prefijo(self, prefijo: str) -> None:
        return None

class CacheRedis:
    def __init__(self, url: str) -> None:
        self._redis = cliente_redis(url)

    def obtener_json(self, clave: str) -> Any | None:
        raw = self._redis.get(clave)
        if raw is None:
            return None
        return json.loads(raw)

    def guardar_json(self, clave: str, valor: Any, ttl_s: int) -> None:
        if ttl_s <= 0:
            return
        self._redis.set(
            clave,
            json.dumps(valor, default=str, separators=(",", ":")),
            ex=ttl_s,
        )

    def borrar(self, clave: str) -> None:
        self._redis.delete(clave)

    def borrar_prefijo(self, prefijo: str) -> None:
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(
                cursor=cursor, match=prefijo + "*", count=200
            )
            if keys:
                self._redis.delete(*keys)
            if cursor == 0:
                break

def construir_cache_respuesta(
    redis_url: str | None, *, activo: bool
) -> CacheRespuesta:
    if not activo:
        return CacheNulo()
    url = (redis_url or "").strip()
    if not url:
        raise ValueError(
            "REDIS_URL es obligatorio para la caché (excepto APP_ENV=test)."
        )
    return CacheRedis(url)

def clave_mapa(filtros: dict[str, str | int | None]) -> str:
    payload = json.dumps(filtros, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return PREF_MAPA + digest

def clave_reputacion(business_id: object) -> str:
    return PREF_REP + str(business_id)

def invalidar_negocio(cache: CacheRespuesta, business_id: object | None = None) -> None:
    cache.borrar_prefijo(PREF_MAPA)
    if business_id is not None:
        cache.borrar(clave_reputacion(business_id))

def invalidar_lecturas_publicas(cache: CacheRespuesta) -> None:

    cache.borrar_prefijo(PREF_MAPA)
    cache.borrar_prefijo(PREF_REP)
