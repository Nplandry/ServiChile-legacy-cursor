

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.dominio.telefono import TelefonoInvalido, normalizar_telefono

TipoCuenta = Literal["persona", "contratista", "proveedor"]
CategoriaNegocio = Literal[
    "tecnologia", "industria", "construccion", "servicios-profesionales", "logistica"
]

_NOMBRE_OK = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .\-]{2,120}$")

def telefono_opcional(value: str | None) -> str | None:
    if value is None:
        return None
    texto = value.strip()
    if not texto:
        return None
    try:
        return normalizar_telefono(texto)
    except TelefonoInvalido as error:
        raise ValueError(str(error)) from None
