

from __future__ import annotations

import re

_SOLO_DIGITOS = re.compile(r"\D+")

class TelefonoInvalido(ValueError):
    pass

def normalizar_telefono(texto: str) -> str:
    raw = (texto or "").strip()
    if not raw:
        raise TelefonoInvalido("Ingrese un teléfono móvil chileno.")

    compacto = re.sub(r"\s+", "", raw)
    if not compacto.startswith("+56"):
        raise TelefonoInvalido(
            "El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678."
        )

    digitos = _SOLO_DIGITOS.sub("", raw)
    if digitos.startswith("56"):
        digitos = digitos[2:]
    if digitos.startswith("0"):
        digitos = digitos[1:]

    if len(digitos) != 9 or not digitos.startswith("9") or not digitos.isdigit():
        raise TelefonoInvalido(
            "Use un móvil chileno válido, p. ej. +56 9 1234 5678."
        )

    return f"+56 9 {digitos[1:5]} {digitos[5:9]}"
