from __future__ import annotations

import uuid

from dataclasses import dataclass, field

from datetime import date, datetime

from app.dominio.docs_empresa import DocsEmpresa

@dataclass
class Perfil:

    edad: int | None = None

    tipo_cuenta: str | None = None

@dataclass
class Usuario:

    id: uuid.UUID

    email: str

    nombre: str

    password_hash: str

    activo: bool = True

    rut: str | None = None

    rut_verificado: bool = False

    telefono: str | None = None

    biometria_verificada: bool = False

    biometria_verificada_en: datetime | None = None

    biometria_ruta: str | None = None

    biometria_sha256: str | None = None

    biometria_bytes: int | None = None

    biometria_ancho: int | None = None

    biometria_alto: int | None = None

    biometria_content_type: str | None = None

    biometria_retener_hasta: datetime | None = None

    cedula_verificada: bool = False

    cedula_verificada_en: datetime | None = None

    cedula_ruta: str | None = None

    cedula_sha256: str | None = None

    cedula_bytes: int | None = None

    cedula_ancho: int | None = None

    cedula_alto: int | None = None

    cedula_content_type: str | None = None

    cedula_retener_hasta: datetime | None = None

    cedula_score: int | None = None

    cedula_rut_ocr: str | None = None

    antecedentes_verificados: bool = False

    antecedentes_verificados_en: datetime | None = None

    antecedentes_anotaciones: bool | None = None

    antecedentes_score: int | None = None

    antecedentes_pades: bool = False

    antecedentes_entidad_emisora: str | None = None

    antecedentes_fecha_emision: date | None = None

    antecedentes_sha256: str | None = None

    antecedentes_glosa: str | None = None

    aval_verificado: bool = False

    aval_verificado_en: datetime | None = None

    aval_score: int | None = None

    aval_tipo: str | None = None

    xp: int = 0

    creado_en: datetime | None = None

    perfil: Perfil | None = None

@dataclass
class Metricas:

    business_id: uuid.UUID

    google_rating_avg: float | None = None

    google_reviews_count: int = 0

    final_score: float = 0.0

    rater_escaneado_en: datetime | None = None

    observables: list | None = None

    actualizado_en: datetime | None = None

@dataclass
class Negocio:

    id: uuid.UUID

    nombre: str

    categoria: str

    latitud: float | None = None

    longitud: float | None = None

    direccion: str | None = None

    descripcion: str | None = None

    servicios: tuple[str, ...] = ()

    industrias: tuple[str, ...] = ()

    contrataciones: tuple[str, ...] = ()

    monto: str | None = None

    plazo: str | None = None

    referencias: tuple[str, ...] = ()

    imagen_url: str | None = None

    logo_url: str | None = None

    requiere_nivel: int = 1

    is_claimed: bool = False

    reclamado_por: uuid.UUID | None = None

    telefono: str | None = None

    sitio_web: str | None = None

    rut_empresa: str | None = None

    docs_empresa: DocsEmpresa = field(default_factory=dict)

    metricas: Metricas | None = None

@dataclass
class Trabajo:

    id: uuid.UUID

    usuario_id: uuid.UUID

    business_id: uuid.UUID

    estado: str

    qr_token: str

    creado_en: datetime | None = None

    actualizado_en: datetime | None = None

@dataclass
class EstadoReporte:

    rut_verificado: bool

    telefono: str | None

    nivel_reporte: int

    estado_reporte: str

    score_confiabilidad: float | None

    edad: int | None

    tipo_cuenta: str | None = None

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

    xp: int = 0

    nivel_xp: int = 1

@dataclass
class ObservableSenal:

    id: str

    etiqueta: str

    detalle: str

    score: int

    peso: str

    grupo: str

    razones: list[str] = field(default_factory=list)

@dataclass
class Reputacion:

    business_id: uuid.UUID

    nombre: str

    categoria: str

    google_rating_avg: float | None

    google_reviews_count: int

    indice_transparencia: float

    indice_pct: int = 0

    docs_verificados: int = 0

    docs_total: int = 0

    docs_empresa: DocsEmpresa | None = None

    actualizado_en: datetime | None = None

    observables: list[ObservableSenal] = field(default_factory=list)

    rater_listo: bool = False

    descargo: str = (
        "Índice global a partir de señales públicas (ficha, sitio, "
        "compras públicas, etc.). No constituye un juicio sobre la calidad del servicio."
    )

@dataclass(frozen=True)
class DocEmpresaVerificado:

    business_id: uuid.UUID
    tipo: str
    verificado: bool
    score: int | None
    senales: tuple[str, ...]
    docs_empresa: DocsEmpresa
    indice_transparencia: float
    indice_pct: int
    docs_verificados: int
    docs_total: int
    verificado_criptograficamente: bool
    entidad_emisora: str | None
    fecha_emision: str | None
    sha256_hash: str | None
    glosa: str | None
    motivo: str

@dataclass
class NegocioEnMapa:

    id: uuid.UUID

    nombre: str

    categoria: str

    latitud: float | None

    longitud: float | None

    direccion: str | None

    descripcion: str | None

    imagen_url: str

    logo_url: str | None

    logo_texto: str

    cta_texto: str

    indice_transparencia: float

    requiere_nivel: int

    is_claimed: bool = False

    indice_pct: int = 0

    servicios: tuple[str, ...] = ()

    industrias: tuple[str, ...] = ()

    contrataciones: tuple[str, ...] = ()

    monto: str | None = None

    plazo: str | None = None

    referencias: tuple[str, ...] = ()

    trabajos_concretados: int = 0

@dataclass
class NegocioTitular:

    id: uuid.UUID

    nombre: str

    categoria: str

    latitud: float | None

    longitud: float | None

    direccion: str | None

    descripcion: str | None

    imagen_url: str

    logo_url: str | None

    logo_texto: str

    cta_texto: str

    indice_transparencia: float

    requiere_nivel: int

    is_claimed: bool = False

    indice_pct: int = 0

    docs_empresa: DocsEmpresa | None = None

    rut_empresa: str | None = None

    telefono: str | None = None

    sitio_web: str | None = None

    rater_listo: bool = False

    servicios: tuple[str, ...] = ()

    industrias: tuple[str, ...] = ()

    contrataciones: tuple[str, ...] = ()

    monto: str | None = None

    plazo: str | None = None

    referencias: tuple[str, ...] = ()

    trabajos_concretados: int = 0

@dataclass
class TokenEmitido:

    access_token: str

    expires_in: int

@dataclass
class ReporteEmitido:

    payload: str

    token: str

    expires_in: int

    expires_at: datetime

    nombre: str

    email: str

    nivel_reporte: int

    estado_reporte: str

    score_confiabilidad: float | None

    rut_verificado: bool

    xp: int = 0

    nivel_xp: int = 1

    tipo_cuenta: str | None = None

    antecedentes_verificados: bool = False

    antecedentes_anotaciones: bool | None = None

@dataclass
class ReporteValidado:

    es_propio: bool

    nombre: str

    nivel_reporte: int

    estado_reporte: str

    score_confiabilidad: float | None

    rut_verificado: bool

    expires_at: datetime

    xp: int = 0

    nivel_xp: int = 1

    tipo_cuenta: str | None = None

    antecedentes_verificados: bool = False

    antecedentes_anotaciones: bool | None = None
