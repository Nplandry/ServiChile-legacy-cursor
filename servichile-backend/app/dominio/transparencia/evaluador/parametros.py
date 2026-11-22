

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CategoriaEvaluador = Literal[
    "ciberseguridad",
    "contractual_datos",
    "fisica_reputacional",
    "presencia_digital",
    "proveedor_estado",
]

GRUPO_FE: dict[CategoriaEvaluador, str] = {
    "ciberseguridad": "ciber",
    "contractual_datos": "contractual",
    "fisica_reputacional": "operativa",
    "presencia_digital": "operativa",
    "proveedor_estado": "legal",
}

@dataclass(frozen=True, slots=True)
class ParametroDef:
    id: str
    nombre: str
    categoria: CategoriaEvaluador
    peso: float = 1.0
    descripcion: str = ""

PARAMETROS: tuple[ParametroDef, ...] = (
    ParametroDef("cyb_https", "HTTPS habilitado", "ciberseguridad", 1.2),
    ParametroDef("cyb_hsts", "Header HSTS", "ciberseguridad", 1.0),
    ParametroDef("cyb_csp", "Content-Security-Policy", "ciberseguridad", 1.0),
    ParametroDef("cyb_xfo", "X-Frame-Options / frame-ancestors", "ciberseguridad", 0.8),
    ParametroDef("cyb_xcto", "X-Content-Type-Options", "ciberseguridad", 0.7),
    ParametroDef("cyb_referrer", "Referrer-Policy", "ciberseguridad", 0.6),
    ParametroDef("cyb_cookies", "Cookies Secure/HttpOnly", "ciberseguridad", 1.0),
    ParametroDef("cyb_mixed", "Sin contenido mixed-content obvio", "ciberseguridad", 0.8),
    ParametroDef("con_privacy", "Tiene política de privacidad", "contractual_datos", 1.4),
    ParametroDef("con_ley_21719", "Cumple normas de datos personales (Ley 21.719)", "contractual_datos", 1.5),
    ParametroDef("con_tyc", "Publica términos y condiciones", "contractual_datos", 1.3),
    ParametroDef("con_sla", "Define plazos o nivel de servicio", "contractual_datos", 1.1),
    ParametroDef("con_dpa", "Explica cómo trata los datos del cliente", "contractual_datos", 1.1),
    ParametroDef("con_clausulas", "Muestra condiciones del servicio", "contractual_datos", 1.0),
    ParametroDef("con_contacto_datos", "Tiene canal para consultas de datos", "contractual_datos", 0.9),
    ParametroDef("con_cookies_notice", "Informa el uso de cookies", "contractual_datos", 0.8),
    ParametroDef("fis_places_exists", "Aparece en Google como negocio", "fisica_reputacional", 1.1),
    ParametroDef("fis_rating", "Nota de clientes en Google", "fisica_reputacional", 1.3),
    ParametroDef("fis_reviews", "Cantidad de reseñas de clientes", "fisica_reputacional", 1.0),
    ParametroDef("fis_address", "Dirección del local publicada", "fisica_reputacional", 1.1),
    ParametroDef("fis_phone", "Teléfono de contacto publicado", "fisica_reputacional", 0.9),
    ParametroDef("fis_hours", "Horario de atención publicado", "fisica_reputacional", 0.6),
    ParametroDef("dig_website", "Tiene sitio web oficial", "presencia_digital", 1.2),
    ParametroDef(
        "est_proveedor",
        "Inscrito como proveedor del Estado",
        "proveedor_estado",
        1.4,
        "Existe en Mercado Público (BuscarProveedor).",
    ),
)

PARAMETROS_POR_ID = {p.id: p for p in PARAMETROS}

IDS_FISICA = (
    "fis_places_exists",
    "fis_rating",
    "fis_reviews",
    "fis_address",
    "fis_phone",
    "fis_hours",
)

IDS_ESTADO = ("est_proveedor",)

IDS_SITIO = (
    "cyb_https",
    "cyb_hsts",
    "cyb_csp",
    "cyb_xfo",
    "cyb_xcto",
    "cyb_referrer",
    "cyb_cookies",
    "cyb_mixed",
    "con_privacy",
    "con_ley_21719",
    "con_tyc",
    "con_sla",
    "con_dpa",
    "con_clausulas",
    "con_contacto_datos",
    "con_cookies_notice",
    "dig_website",
)

def nota_desde_puntaje(puntaje: float) -> str:
    if puntaje >= 85:
        return "A"
    if puntaje >= 70:
        return "B"
    if puntaje >= 55:
        return "C"
    if puntaje >= 40:
        return "D"
    return "F"
