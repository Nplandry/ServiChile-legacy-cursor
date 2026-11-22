

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

PRECIO_INFORME_CLP = 9990

ESTADO_PENDIENTE = "pendiente"
ESTADO_CONFIRMANDO = "confirmando"
ESTADO_AUTORIZADO = "autorizado"
ESTADO_RECHAZADO = "rechazado"
ESTADO_ERROR = "error"
ESTADO_ANULADO = "anulado"

@dataclass(frozen=True)
class CatalogoPagoInforme:
    monto: int
    moneda: str = "CLP"
    producto: str = "informe_proveedor"

@dataclass(frozen=True)
class ResumenComprasInforme:
    autorizadas_mes: int
    gastado_mes: int
    monto_unitario: int

@dataclass
class CompraInforme:
    id: uuid.UUID
    usuario_id: uuid.UUID
    business_id: uuid.UUID
    buy_order: str
    monto: int
    estado: str
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
class CanalReclamo:
    email: str
    whatsapp: str
    instruccion: str

@dataclass(frozen=True)
class InicioPagoInforme:
    buy_order: str
    token: str
    url: str
    monto: int
    business_id: uuid.UUID
    reclamo: CanalReclamo

@dataclass(frozen=True)
class ConfirmacionPagoInforme:
    buy_order: str
    estado: str
    autorizado: bool
    business_id: uuid.UUID
    monto: int
    response_code: int | None
    authorization_code: str | None
    error_codigo: str | None
    error_detalle: str | None
    reclamo: CanalReclamo
    enviado: bool = False
    destino: str | None = None
    qr_payload: str | None = None
    expires_at: datetime | None = None
    print_token: str | None = None
