

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class TrabajoEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    business_id: UUID

class TrabajoSalida(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    business_id: UUID

    estado: Literal["abierto", "concretado", "no_concretado", "cancelado"]

    qr_token: str

    creado_en: datetime

class ConcretarEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    qr_token: str = Field(min_length=10, max_length=64)

class EliminarCuentaEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)
