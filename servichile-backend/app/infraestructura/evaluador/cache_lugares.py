

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_TTL_S = 7 * 24 * 3600
_MEM: dict[str, tuple[float, dict[str, Any]]] = {}

def _dir() -> Path:
    root = Path(__file__).resolve().parents[3] / ".cache" / "places"
    root.mkdir(parents=True, exist_ok=True)
    return root

def _clave(dominio: str) -> str:
    return (dominio or "").strip().lower().removeprefix("www.").split("/")[0]

def _ruta(dominio: str) -> Path:
    seguro = _clave(dominio).replace(".", "_") or "desconocido"
    return _dir() / f"{seguro}.json"

def obtener(dominio: str) -> dict[str, Any] | None:
    k = _clave(dominio)
    if not k:
        return None
    now = time.time()
    hit = _MEM.get(k)
    if hit and now - hit[0] <= _TTL_S:
        return hit[1]
    path = _ruta(k)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    ts = float(raw.get("guardado_en") or raw.get("saved_at") or 0)
    if ts and now - ts > _TTL_S:
        return None
    carga = raw.get("carga") or raw.get("payload")
    if not isinstance(carga, dict):
        return None
    _MEM[k] = (ts or now, carga)
    return carga

def guardar(dominio: str, carga: dict[str, Any]) -> None:
    k = _clave(dominio)
    if not k or not isinstance(carga, dict):
        return
    now = time.time()
    _MEM[k] = (now, carga)
    path = _ruta(k)
    try:
        path.write_text(
            json.dumps({"guardado_en": now, "carga": carga}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass

def limpiar(dominio: str | None = None) -> None:
    if dominio:
        k = _clave(dominio)
        _MEM.pop(k, None)
        path = _ruta(k)
        if path.is_file():
            try:
                path.unlink()
            except OSError:
                pass
        return
    _MEM.clear()
