from __future__ import annotations

from typing import Any

import httpx

def obtener_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    tiempo_espera: float = 2.0,
) -> tuple[bool, Any, str | None]:
    try:
        with httpx.Client(timeout=tiempo_espera, follow_redirects=True) as cliente:
            r = cliente.get(url, params=params, headers=headers)
            r.raise_for_status()
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                return True, r.json(), None
            return True, r.text, None
    except Exception as exc:
        return False, None, str(exc) or type(exc).__name__

def enviar_json(
    url: str,
    carga: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    tiempo_espera: float = 2.0,
) -> tuple[bool, Any, str | None]:
    try:
        with httpx.Client(timeout=tiempo_espera, follow_redirects=True) as cliente:
            r = cliente.post(url, json=carga, headers=headers)
            r.raise_for_status()
            return True, r.json(), None
    except Exception as exc:
        return False, None, str(exc) or type(exc).__name__
