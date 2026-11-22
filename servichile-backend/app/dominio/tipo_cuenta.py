from __future__ import annotations

TIPOS_CUENTA = frozenset({"persona", "contratista", "proveedor"})

TIPO_PROVEEDOR = "proveedor"

TIPOS_PERSONA_LIKE = frozenset({"persona", "contratista"})

_LEGACY = {"empresa": "proveedor"}

def normalizar(tipo: str | None) -> str | None:

    if tipo is None:

        return None

    clave = str(tipo).strip().lower()

    if not clave:

        return None

    return _LEGACY.get(clave, clave)

def es_proveedor(tipo: str | None) -> bool:

    return normalizar(tipo) == TIPO_PROVEEDOR

def es_persona_like(tipo: str | None) -> bool:

    return normalizar(tipo) in TIPOS_PERSONA_LIKE

def tipo_de_usuario(usuario) -> str | None:

    perfil = getattr(usuario, "perfil", None)

    return normalizar(getattr(perfil, "tipo_cuenta", None) if perfil else None)
