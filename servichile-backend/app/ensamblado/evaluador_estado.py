

from __future__ import annotations

import json
import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_LOCK = Lock()
_PATH = Path("var/evaluador_estado.json")
_REDIS_KEY = "servichile:evaluador_estado"
_INSTANCIA = os.environ.get("HOSTNAME") or socket.gethostname() or "local"
_log = logging.getLogger(__name__)

@dataclass
class EstadoEvaluador:
    ok: bool = True
    ultimo_exito: str | None = None
    ultimo_error: str | None = None
    ultimo_lote: int | None = None
    instancia: str = _INSTANCIA

def _redis_client():
    try:
        from app.configuracion import obtener_configuracion
        from app.infraestructura.redis_cliente import cliente_redis

        url = (obtener_configuracion().redis_url or "").strip()
        if not url:
            return None
        return cliente_redis(url)
    except Exception:
        _log.warning("Cliente Redis de evaluador_estado no disponible", exc_info=True)
        return None

def _cargar_archivo() -> EstadoEvaluador:
    try:
        if not _PATH.is_file():
            return EstadoEvaluador()
        raw = json.loads(_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return EstadoEvaluador()
        return EstadoEvaluador(
            ok=bool(raw.get("ok", True)),
            ultimo_exito=raw.get("ultimo_exito"),
            ultimo_error=raw.get("ultimo_error"),
            ultimo_lote=raw.get("ultimo_lote"),
            instancia=str(raw.get("instancia") or _INSTANCIA),
        )
    except Exception:
        _log.warning("No se pudo leer %s", _PATH, exc_info=True)
        return EstadoEvaluador()

def _cargar_redis() -> EstadoEvaluador | None:
    client = _redis_client()
    if client is None:
        return None
    try:
        raw = client.get(_REDIS_KEY)
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return EstadoEvaluador(
            ok=bool(data.get("ok", True)),
            ultimo_exito=data.get("ultimo_exito"),
            ultimo_error=data.get("ultimo_error"),
            ultimo_lote=data.get("ultimo_lote"),
            instancia=str(data.get("instancia") or _INSTANCIA),
        )
    except Exception:
        _log.warning("No se pudo leer estado del evaluador en Redis", exc_info=True)
        return None

def _payload(estado: EstadoEvaluador) -> dict[str, object]:
    return {
        "ok": estado.ok,
        "ultimo_exito": estado.ultimo_exito,
        "ultimo_error": estado.ultimo_error,
        "ultimo_lote": estado.ultimo_lote,
        "instancia": estado.instancia,
    }

def _persistir(estado: EstadoEvaluador) -> None:
    data = _payload(estado)
    try:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_PATH)
    except Exception:
        _log.warning("No se pudo persistir estado del evaluador en disco", exc_info=True)
    client = _redis_client()
    if client is None:
        return
    try:
        client.set(_REDIS_KEY, json.dumps(data, ensure_ascii=False), ex=86_400)
    except Exception:
        _log.warning("No se pudo persistir estado del evaluador en Redis", exc_info=True)

_estado = _cargar_redis() or _cargar_archivo()

def marcar_exito(n: int) -> None:
    with _LOCK:
        _estado.ok = True
        _estado.ultimo_exito = datetime.now(timezone.utc).isoformat()
        _estado.ultimo_lote = int(n)
        _estado.ultimo_error = None
        _estado.instancia = _INSTANCIA
        _persistir(_estado)

def marcar_error(mensaje: str) -> None:
    with _LOCK:
        _estado.ok = False
        _estado.ultimo_error = (mensaje or "error")[:500]
        _estado.instancia = _INSTANCIA
        _persistir(_estado)

def snapshot() -> dict[str, object]:
    with _LOCK:
        remoto = _cargar_redis()
        if remoto is not None:
            return _payload(remoto)
        return _payload(_estado)
