

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from app.dominio.texto_pdf import compact, extraer_fechas, extraer_ruts, texto_lower

PerfilPades = Literal[
    "antecedentes",
    "antecedentes_rl",
    "inicio_actividades",
    "carpeta_tributaria",
    "vigencia_sociedad",
    "vigencia_poderes",
    "poder_representante",
    "f30",
    "no_quiebra",
    "constitucion",
]

MAX_ANTIGUEDAD_DIAS = 60

_PERFILES: dict[str, dict] = {
    "antecedentes": {
        "entidad": "REGISTRO_CIVIL",
        "keywords": (
            "registrocivil",
            "registro civil",
            "acepta.com",
            "acepta",
            "firma electronica avanzada",
            "e-sign",
            "esign",
        ),
    },
    "antecedentes_rl": {
        "entidad": "REGISTRO_CIVIL",
        "keywords": (
            "registrocivil",
            "registro civil",
            "acepta.com",
            "acepta",
            "firma electronica avanzada",
            "e-sign",
            "esign",
        ),
    },
    "inicio_actividades": {
        "entidad": "SII",
        "keywords": (
            "servicio de impuestos internos",
            "impuestos internos",
            "sii.cl",
            "sii",
            "acepta.com",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
        ),
        "keywords_obligatorias_algunas": (
            "servicio de impuestos internos",
            "impuestos internos",
            "sii.cl",
            "sii",
        ),
    },
    "carpeta_tributaria": {
        "entidad": "SII",
        "keywords": (
            "servicio de impuestos internos",
            "impuestos internos",
            "sii.cl",
            "sii",
            "acepta.com",
            "acepta",
            "e-sign",
            "esign",
            "carpeta tributaria",
        ),
        "keywords_obligatorias_algunas": (
            "servicio de impuestos internos",
            "impuestos internos",
            "sii.cl",
            "sii",
            "carpeta tributaria",
        ),
    },
    "vigencia_sociedad": {
        "entidad": "RES_CBR",
        "keywords": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "bienes raices",
            "registro de comercio",
            "vigente",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
            "subsecretaria de economia",
            "economia",
        ),
        "keywords_obligatorias_algunas": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "registro de comercio",
            "bienes raices",
            "subsecretaria de economia",
        ),
    },
    "vigencia_poderes": {
        "entidad": "RES_CBR_NOTARIA",
        "keywords": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "notaria",
            "notario",
            "poder",
            "facultades",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
        ),
        "keywords_obligatorias_algunas": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "notaria",
            "notario",
            "poder",
        ),
    },
    "poder_representante": {
        "entidad": "RES_CBR_NOTARIA",
        "keywords": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "notaria",
            "notario",
            "poder",
            "facultades",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
        ),
        "keywords_obligatorias_algunas": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "notaria",
            "notario",
            "poder",
        ),
    },
    "constitucion": {
        "entidad": "NOTARIA_RES",
        "keywords": (
            "notaria",
            "notario",
            "escritura",
            "registro de empresas",
            "conservador",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
        ),
        "keywords_obligatorias_algunas": (
            "notaria",
            "notario",
            "escritura",
            "registro de empresas",
            "conservador",
        ),
    },
    "f30": {
        "entidad": "DIRECCION_TRABAJO",
        "keywords": (
            "direccion del trabajo",
            "direccion del trabajo",
            "midt",
            "dt.gob",
            "inspeccion del trabajo",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
            "certinet",
            "f30",
        ),
        "keywords_obligatorias_algunas": (
            "direccion del trabajo",
            "midt",
            "dt.gob",
            "inspeccion del trabajo",
            "f30",
        ),
    },
    "no_quiebra": {
        "entidad": "SUPERIR",
        "keywords": (
            "superintendencia de insolvencia",
            "reemprendimiento",
            "boletin concursal",
            "superir",
            "acepta",
            "e-sign",
            "esign",
            "firma electronica avanzada",
        ),
        "keywords_obligatorias_algunas": (
            "superintendencia de insolvencia",
            "reemprendimiento",
            "boletin concursal",
            "superir",
        ),
    },
}

_GLOSAS: dict[str, tuple[str, ...]] = {
    "antecedentes": (
        "sin antecedentes",
        "sin anotaciones",
        "sin anotaciones vigentes",
    ),
    "antecedentes_rl": (
        "sin antecedentes",
        "sin anotaciones",
        "sin anotaciones vigentes",
    ),
    "inicio_actividades": (
        "inicio de actividades",
        "inicio actividades",
        "empresa vigente",
        "contribuyente",
        "factura electronica",
        "dte",
    ),
    "carpeta_tributaria": (
        "carpeta tributaria",
        "evaluacion de proveedores",
        "solicitar creditos",
        "formulario 29",
        "formulario 22",
        "f29",
        "f22",
        "sin observaciones",
    ),
    "vigencia_sociedad": (
        "empresa vigente",
        "sociedad vigente",
        "vigente",
        "no disuelta",
        "en vigencia",
    ),
    "vigencia_poderes": (
        "facultades",
        "representante legal",
        "poder vigente",
        "vigente",
    ),
    "poder_representante": (
        "facultades",
        "representante legal",
        "poder",
        "mandato",
    ),
    "constitucion": (
        "constitucion",
        "escritura publica",
        "estatutos",
        "sociedad",
    ),
    "f30": (
        "sin multas",
        "no registra multas",
        "cotizaciones",
        "al dia",
        "sin deudas previsionales",
        "f30",
        "antecedentes laborales",
    ),
    "no_quiebra": (
        "no registra",
        "sin procedimientos",
        "no se encuentra",
        "sin liquidacion",
        "sin reorganizacion",
        "boletin concursal",
    ),
}

_MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

@dataclass(frozen=True)
class ResultadoPades:
    ok: bool
    intact: bool
    trusted: bool
    coverage_ok: bool
    entidad_emisora: str | None
    subject: str | None
    issuer: str | None
    sha256_hash: str
    motivo: str
    senales: tuple[str, ...]
    pdf_firmado_bytes: bytes | None = None

def sha256_hex(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()

def perfil_config(perfil: str) -> dict:
    return _PERFILES[perfil]

def emisor_coincide(subject: str, issuer: str, perfil: str) -> bool:
    cfg = _PERFILES.get(perfil)
    if not cfg:
        return False
    blob = texto_lower(f"{subject} | {issuer}")
    if not any(k in blob for k in cfg["keywords"]):
        return False
    oblig = cfg.get("keywords_obligatorias_algunas")
    if oblig and not any(k in blob for k in oblig):
        return False
    return True

def entidad_de(perfil: str) -> str:
    return str(_PERFILES[perfil]["entidad"])

def parsear_fecha_emision(texto: str) -> date | None:
    m = re.search(
        r"FECHA\s*EMISI[OÓ]N\s*:?\s*(\d{1,2})\s+([A-Za-záéíóúÁÉÍÓÚ]+)\s+(\d{4})",
        texto or "",
        re.I,
    )
    if m:
        mes = _MESES.get(m.group(2).lower())
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                pass

    m = re.search(
        r"\b(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b",
        texto or "",
        re.I,
    )
    if m:
        mes = _MESES.get(m.group(2).lower())
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                pass

    for raw in extraer_fechas(texto):
        m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", raw)
        if not m:
            continue
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            continue
    return None

def fecha_dentro_ventana(
    fecha: date | datetime | None,
    *,
    hoy: date | None = None,
    max_dias: int = MAX_ANTIGUEDAD_DIAS,
) -> bool:
    if fecha is None:
        return False
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    ref = hoy or date.today()
    if fecha > ref + timedelta(days=1):
        return False
    return (ref - fecha).days <= max_dias

def detectar_glosa(texto: str, perfil: str) -> str | None:
    low = texto_lower(texto)
    glosas = _GLOSAS.get(perfil, ())
    for g in glosas:
        if g in low or compact(g) in compact(texto):
            return g
    return None

def rut_coincide_con_empresa(texto: str, rut_empresa: str | None) -> str | None:
    ruts = extraer_ruts(texto)
    if not ruts:
        return None
    if not rut_empresa:
        return ruts[0]
    from app.dominio.rut import RutInvalido, normalizar_rut

    try:
        perfil = normalizar_rut(rut_empresa)
    except (RutInvalido, ValueError):
        return ruts[0]
    return perfil if perfil in ruts else None
