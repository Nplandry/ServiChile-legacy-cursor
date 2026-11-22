

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.api.esquemas.comunes import TipoCuenta, _NOMBRE_OK, telefono_opcional

class PerfilEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    edad: int | None = Field(default=None, ge=14, le=120)

    tipo_cuenta: TipoCuenta | None = None

    rut: str | None = Field(default=None, min_length=3, max_length=15)

    telefono: str | None = Field(default=None, max_length=30)

    @field_validator("telefono")
    @classmethod
    def _telefono_chileno(cls, value: str | None) -> str | None:

        return telefono_opcional(value)

class PerfilRegistroEntrada(BaseModel):

    model_config = ConfigDict(extra="forbid")

    tipo_cuenta: TipoCuenta

    edad: int | None = Field(default=None, ge=14, le=120)

class PerfilSalida(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    rut_verificado: bool = False

    telefono: str | None = None

    nivel_reporte: Literal[1] = 1

    estado_reporte: Literal["basico", "pendiente", "verificado", "rechazado"] = (
        "basico"
    )

    score_confiabilidad: float | None = None

    biometria_verificada: bool = False

    biometria_verificada_en: datetime | None = None

    biometria_retener_hasta: datetime | None = None

    biometria_bytes: int | None = None

    cedula_verificada: bool = False

    cedula_verificada_en: datetime | None = None

    cedula_retener_hasta: datetime | None = None

    cedula_bytes: int | None = None

    cedula_score: int | None = None

    antecedentes_verificados: bool = False

    antecedentes_verificados_en: datetime | None = None

    antecedentes_anotaciones: bool | None = None

    antecedentes_score: int | None = None

    aval_verificado: bool = False

    aval_verificado_en: datetime | None = None

    aval_score: int | None = None

    aval_tipo: str | None = None

    xp: int = Field(default=0, ge=0)

    nivel_xp: int = Field(default=1, ge=1, le=3)

    edad: int | None = None

    tipo_cuenta: TipoCuenta | None = None

class BiometriaSalida(BaseModel):

    biometria_verificada: bool

    biometria_verificada_en: datetime

    biometria_retener_hasta: datetime | None = None

    biometria_bytes: int | None = None

    xp: int = Field(default=0, ge=0)

    nivel_xp: int = Field(default=1, ge=1, le=3)

    mensaje: str = (
        "Verificación biométrica completada. Se guardó una copia comprimida "
        "con acceso restringido y retención limitada; se borra al eliminar la cuenta."
    )

class CedulaSalida(BaseModel):

    cedula_verificada: bool

    cedula_verificada_en: datetime | None = None

    cedula_retener_hasta: datetime | None = None

    cedula_bytes: int | None = None

    cedula_score: int | None = None

    rut_verificado: bool = False

    xp: int = Field(default=0, ge=0)

    nivel_xp: int = Field(default=1, ge=1, le=3)

    senales: list[str] = Field(default_factory=list)

    face_score: float | None = None

    motivo: str = (
        "Cédula validada."
    )

class AntecedentesSalida(BaseModel):

    antecedentes_verificados: bool

    antecedentes_verificados_en: datetime | None = None

    antecedentes_anotaciones: bool | None = None

    antecedentes_score: int | None = None

    verificado_criptograficamente: bool = False

    entidad_emisora: str | None = None

    fecha_emision: str | None = None

    sha256_hash: str | None = None

    glosa: str | None = None

    xp: int = Field(default=0, ge=0)

    nivel_xp: int = Field(default=1, ge=1, le=3)

    senales: list[str] = Field(default_factory=list)

    motivo: str = "Certificado de antecedentes validado."

class AvalSalida(BaseModel):

    aval_verificado: bool

    aval_verificado_en: datetime | None = None

    aval_score: int | None = None

    aval_tipo: str | None = None

    xp: int = Field(default=0, ge=0)

    nivel_xp: int = Field(default=1, ge=1, le=3)

    senales: list[str] = Field(default_factory=list)

    motivo: str = "Aval/garantía validado."

class RegistroEntrada(BaseModel):

    email: EmailStr

    nombre: str = Field(min_length=2, max_length=120)

    password: str = Field(min_length=8, max_length=128)

    perfil: PerfilRegistroEntrada

    @field_validator("nombre")
    @classmethod
    def _strip_nombre(cls, value: str) -> str:

        value = " ".join(value.strip().split())

        if len(value) < 2:

            raise ValueError("Ingrese su nombre completo.")

        if not _NOMBRE_OK.fullmatch(value):

            raise ValueError(
                "El nombre solo puede incluir letras, espacios y . '-."
            )

        return value

    @field_validator("email")
    @classmethod
    def _email_minusculas(cls, value: EmailStr) -> str:

        return str(value).strip().lower()

class LoginEntrada(BaseModel):

    email: EmailStr

    password: str = Field(min_length=1, max_length=128)

class TokenSalida(BaseModel):

    access_token: str

    token_type: Literal["bearer"] = "bearer"

    expires_in: int

class UsuarioSalida(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    email: EmailStr

    nombre: str

    creado_en: datetime

    perfil: PerfilSalida = Field(default_factory=PerfilSalida)

    @field_validator("perfil", mode="before")
    @classmethod
    def _perfil_vacio(cls, value: object) -> object:

        return PerfilSalida() if value is None else value

