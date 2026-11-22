

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

PRECIO_PUBLICACION_CLP = 8990

ESTADO_PENDIENTE = "pendiente"
ESTADO_CONFIRMANDO = "confirmando"
ESTADO_AUTORIZADO = "autorizado"
ESTADO_RESERVADO = "reservado"
ESTADO_CONSUMIDO = "consumido"
ESTADO_RECHAZADO = "rechazado"
ESTADO_ERROR = "error"
ESTADO_ANULADO = "anulado"

def formato_monto_clp(monto: int) -> str:

    return "$" + f"{int(monto):,}".replace(",", ".")

@dataclass(frozen=True)
class CatalogoPagoPublicacion:
    monto: int
    moneda: str = "CLP"
    producto: str = "publicacion_empresa"

@dataclass
class CompraPublicacion:
    id: uuid.UUID
    usuario_id: uuid.UUID
    buy_order: str
    monto: int
    estado: str
    business_id: uuid.UUID | None = None
    token: str | None = None
    response_code: int | None = None
    authorization_code: str | None = None
    payment_type_code: str | None = None
    card_last4: str | None = None
    error_codigo: str | None = None
    error_detalle: str | None = None
    creado_en: datetime | None = None
    actualizado_en: datetime | None = None

@dataclass(frozen=True)
class CanalReclamoPublicacion:
    email: str
    whatsapp: str
    instruccion: str

@dataclass(frozen=True)
class InicioPagoPublicacion:
    buy_order: str
    token: str
    url: str
    monto: int
    reclamo: CanalReclamoPublicacion

@dataclass(frozen=True)
class ConfirmacionPagoPublicacion:
    buy_order: str
    estado: str
    autorizado: bool
    monto: int
    response_code: int | None
    authorization_code: str | None
    error_codigo: str | None
    error_detalle: str | None
    reclamo: CanalReclamoPublicacion
    business_id: uuid.UUID | None = None
    consumido: bool = False
