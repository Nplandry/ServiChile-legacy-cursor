

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.api.esquemas.comunes import TipoCuenta

class ReporteSalida(BaseModel):

    payload: str

    token: str

    expires_in: int

    expires_at: datetime

    nombre: str

    email: EmailStr

    nivel_reporte: Literal[1] = 1

    estado_reporte: Literal["basico", "pendiente", "verificado", "rechazado"]

    score_confiabilidad: float | None = None

    rut_verificado: bool = False

    xp: int = 0

    nivel_xp: int = Field(default=1, ge=1, le=3)

    tipo_cuenta: TipoCuenta | None = None

    antecedentes_verificados: bool = False

    antecedentes_anotaciones: bool | None = None

class ReporteValidarEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    payload: str = Field(min_length=10, max_length=2048)

class ReporteValidacionSalida(BaseModel):

    es_propio: bool

    nombre: str

    nivel_reporte: Literal[1] = 1

    estado_reporte: Literal["basico", "pendiente", "verificado", "rechazado"]

    score_confiabilidad: float | None = None

    rut_verificado: bool = False

    expires_at: datetime

    xp: int = 0

    nivel_xp: int = Field(default=1, ge=1, le=3)

    tipo_cuenta: TipoCuenta | None = None

    antecedentes_verificados: bool = False

    antecedentes_anotaciones: bool | None = None
