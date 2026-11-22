from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

class IniciarPagoInformeEntrada(BaseModel):
    business_id: UUID
    return_url: str | None = Field(default=None, max_length=512)

class CatalogoPagoInformeSalida(BaseModel):
    monto: int = Field(ge=1)
    moneda: str = "CLP"
    producto: str = "informe_proveedor"

class ResumenComprasInformeSalida(BaseModel):
    autorizadas_mes: int = Field(ge=0)
    gastado_mes: int = Field(ge=0)
    monto_unitario: int = Field(ge=1)

class CanalReclamoSalida(BaseModel):
    email: str
    whatsapp: str
    instruccion: str

class InicioPagoInformeSalida(BaseModel):
    buy_order: str
    token: str
    url: str
    monto: int = Field(ge=1)
    business_id: UUID
    reclamo: CanalReclamoSalida

class ConfirmarPagoInformeEntrada(BaseModel):
    token: str = Field(min_length=8, max_length=128)

class AnularPagoInformeEntrada(BaseModel):
    buy_order: str = Field(min_length=3, max_length=26)
    motivo: str | None = Field(default=None, max_length=500)

class ConfirmacionPagoInformeSalida(BaseModel):
    buy_order: str
    estado: str
    autorizado: bool
    business_id: UUID
    monto: int
    response_code: int | None = None
    authorization_code: str | None = None
    error_codigo: str | None = None
    error_detalle: str | None = None
    reclamo: CanalReclamoSalida
    enviado: bool = False
    destino: str | None = None
    qr_payload: str | None = None
    expires_at: datetime | None = None
    print_token: str | None = None

class RecuperarPagoInformeEntrada(BaseModel):
    buy_order: str = Field(min_length=3, max_length=26)

class VerificarPrintEntrada(BaseModel):
    business_id: UUID
    print_token: str = Field(min_length=16, max_length=256)

class IniciarPagoPublicacionEntrada(BaseModel):
    return_url: str | None = Field(default=None, max_length=512)

class CatalogoPagoPublicacionSalida(BaseModel):
    monto: int = Field(ge=1)
    moneda: str = "CLP"
    producto: str = "publicacion_empresa"

class InicioPagoPublicacionSalida(BaseModel):
    buy_order: str
    token: str
    url: str
    monto: int = Field(ge=1)
    reclamo: CanalReclamoSalida

class ConfirmarPagoPublicacionEntrada(BaseModel):
    token: str = Field(min_length=8, max_length=128)

class AnularPagoPublicacionEntrada(BaseModel):
    buy_order: str = Field(min_length=3, max_length=26)
    motivo: str | None = Field(default=None, max_length=500)

class RecuperarPagoPublicacionEntrada(BaseModel):
    buy_order: str = Field(min_length=3, max_length=26)

class ConfirmacionPagoPublicacionSalida(BaseModel):
    buy_order: str
    estado: str
    autorizado: bool
    monto: int
    response_code: int | None = None
    authorization_code: str | None = None
    error_codigo: str | None = None
    error_detalle: str | None = None
    reclamo: CanalReclamoSalida
    business_id: UUID | None = None
    consumido: bool = False
