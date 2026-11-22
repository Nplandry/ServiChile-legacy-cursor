

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.dominio.docs_empresa_meta import (
    DOCS_EMPRESA_VIGENCIA_DIAS,
    DocsEmpresa,
    MetaDocEmpresa,
    docs_empresa_a_raw,
    docs_empresa_desde_raw,
    meta_doc_desde_raw,
    meta_doc_esta_vigente,
    vence_en_efectivo,
)
from app.dominio.rut import RutInvalido, normalizar_rut
from app.dominio.texto_pdf import (
    MIN_TEXTO_ALNUM,
    PDF_MAX_BYTES,
    contiene_alguna,
    contar_alnum,
    extraer_fechas,
    extraer_ruts,
    nombre_coincide,
)

DOCS_EMPRESA_MAX_BYTES = PDF_MAX_BYTES
UMBRAL_ACEPTACION = 70

TipoDocEmpresa = Literal[

    "carpeta_tributaria",
    "inicio_actividades",
    "vigencia_sociedad",
    "vigencia_poderes",
    "poder_representante",
    "constitucion",
    "f30",
    "no_quiebra",
    "antecedentes_rl",

    "patente",
    "titularidad_cuenta",
]

TIPOS_DOC_EMPRESA: tuple[TipoDocEmpresa, ...] = (
    "carpeta_tributaria",
    "inicio_actividades",
    "vigencia_sociedad",
    "vigencia_poderes",
    "poder_representante",
    "constitucion",
    "f30",
    "no_quiebra",
    "antecedentes_rl",
    "patente",
    "titularidad_cuenta",
)

TIPOS_PADES: frozenset[str] = frozenset(
    {
        "carpeta_tributaria",
        "inicio_actividades",
        "vigencia_sociedad",
        "vigencia_poderes",
        "poder_representante",
        "constitucion",
        "f30",
        "no_quiebra",
        "antecedentes_rl",
    }
)

TIPOS_PDF: frozenset[str] = TIPOS_PADES | frozenset({"patente", "titularidad_cuenta"})

_OBLIGATORIAS = frozenset({"texto-real", "palabra-clave", "tipo-ok"})
_REGLAS: dict[str, dict] = {
    "carpeta_tributaria": {
        "label": "Carpeta Tributaria Electrónica (SII)",
        "grupo": 1,
        "perfil_pades": "carpeta_tributaria",
        "keywords": (
            "carpeta tributaria",
            "servicio de impuestos internos",
            "formulario 29",
            "formulario 22",
            "f29",
            "f22",
            "evaluacion de proveedores",
            "solicitar creditos",
            "contribuyente",
        ),
        "emisores": ("servicio de impuestos internos", "sii", "impuestos internos"),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "inicio_actividades": {
        "label": "Inicio de actividades / Situación tributaria (SII)",
        "grupo": 1,
        "perfil_pades": "inicio_actividades",
        "keywords": (
            "inicio de actividades",
            "inicio actividades",
            "situacion tributaria",
            "servicio de impuestos internos",
            "sii",
            "giro",
            "contribuyente",
            "factura electronica",
            "dte",
        ),
        "emisores": ("servicio de impuestos internos", "sii", "impuestos internos"),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "vigencia_sociedad": {
        "label": "Certificado de vigencia de la sociedad",
        "grupo": 1,
        "perfil_pades": "vigencia_sociedad",
        "keywords": (
            "vigencia",
            "empresa vigente",
            "sociedad vigente",
            "registro de empresas",
            "tu empresa en un dia",
            "conservador",
            "registro de comercio",
        ),
        "emisores": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "registro de comercio",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "vigencia_poderes": {
        "label": "Certificado de vigencia de poderes",
        "grupo": 1,
        "perfil_pades": "vigencia_poderes",
        "keywords": (
            "vigencia de poderes",
            "poderes",
            "facultades",
            "representante legal",
            "registro de empresas",
            "notaria",
        ),
        "emisores": (
            "tu empresa en un dia",
            "registro de empresas",
            "conservador",
            "notaria",
            "notario",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "poder_representante": {
        "label": "Poder del representante legal",
        "grupo": 1,
        "perfil_pades": "poder_representante",
        "keywords": (
            "poder",
            "representante legal",
            "mandato",
            "facultades",
            "apoderado",
            "escritura publica",
        ),
        "emisores": ("notaria", "notario", "escritura publica", "registro de empresas"),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "constitucion": {
        "label": "Constitución / escritura de la sociedad",
        "grupo": 1,
        "perfil_pades": "constitucion",
        "keywords": (
            "constitucion",
            "escritura publica",
            "sociedad",
            "estatutos",
            "razon social",
            "registro de comercio",
            "diario oficial",
        ),
        "emisores": (
            "notaria",
            "notario",
            "conservador",
            "registro de comercio",
            "diario oficial",
            "registro de empresas",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": False,
    },
    "f30": {
        "label": "Certificado F30 (Dirección del Trabajo)",
        "grupo": 1,
        "perfil_pades": "f30",
        "keywords": (
            "f30",
            "antecedentes laborales",
            "previsionales",
            "direccion del trabajo",
            "cotizaciones",
            "multas",
        ),
        "emisores": (
            "direccion del trabajo",
            "inspeccion del trabajo",
            "midt",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "no_quiebra": {
        "label": "Certificado de no quiebra / procedimientos concursales",
        "grupo": 1,
        "perfil_pades": "no_quiebra",
        "keywords": (
            "quiebra",
            "liquidacion",
            "reorganizacion",
            "boletin concursal",
            "insolvencencia",
            "superintendencia",
        ),
        "emisores": (
            "superintendencia de insolvencia",
            "reemprendimiento",
            "boletin concursal",
            "superir",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
    "antecedentes_rl": {
        "label": "Antecedentes del representante legal (Registro Civil)",
        "grupo": 1,
        "perfil_pades": "antecedentes_rl",
        "keywords": (
            "certificado de antecedentes",
            "registro civil",
            "fines particulares",
            "sin anotaciones",
            "sin antecedentes",
        ),
        "emisores": ("registro civil", "identificacion"),
        "exige_rut_empresa": False,
        "exige_fecha_reciente": True,
    },
    "patente": {
        "label": "Patente municipal vigente",
        "grupo": 2,
        "perfil_pades": None,
        "keywords": (
            "patente",
            "patente municipal",
            "patente comercial",
            "municipalidad",
            "ilustre municipalidad",
            "permiso de funcionamiento",
            "giro",
        ),
        "emisores": (
            "municipalidad",
            "municipio",
            "ilustre municipalidad",
            "direccion de rentas",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": False,
    },
    "titularidad_cuenta": {
        "label": "Comprobante de titularidad de cuenta bancaria empresa",
        "grupo": 2,
        "perfil_pades": None,
        "keywords": (
            "titularidad",
            "cuenta corriente",
            "cuenta vista",
            "banco",
            "rut",
            "titular",
            "certificado de cuenta",
        ),
        "emisores": (
            "banco",
            "bancoestado",
            "banco de chile",
            "santander",
            "bci",
            "itau",
            "scotiabank",
            "security",
            "falabella",
        ),
        "exige_rut_empresa": True,
        "exige_fecha_reciente": True,
    },
}

@dataclass(frozen=True)
class ResultadoDocEmpresa:
    aceptado: bool
    score: int
    tipo: TipoDocEmpresa
    senales: tuple[str, ...]
    motivo: str
    rut_detectado: str | None = None
    verificado_criptograficamente: bool = False
    entidad_emisora: str | None = None
    fecha_emision: str | None = None
    sha256_hash: str | None = None
    glosa: str | None = None
    grupo: int = 1

def es_tipo_doc_empresa(valor: str) -> bool:
    return valor in TIPOS_DOC_EMPRESA

def label_tipo(tipo: TipoDocEmpresa) -> str:
    return str(_REGLAS[tipo]["label"])

def perfil_pades_de(tipo: TipoDocEmpresa) -> str | None:
    return _REGLAS[tipo].get("perfil_pades")

def validar_doc_empresa(
    *,
    tipo: TipoDocEmpresa,
    texto: str,
    rut_empresa: str | None = None,
    nombre_empresa: str | None = None,
    pades_ok: bool = False,
    entidad_emisora: str | None = None,
    sha256_hash: str | None = None,
) -> ResultadoDocEmpresa:
    from app.dominio.pades import (
        detectar_glosa,
        fecha_dentro_ventana,
        parsear_fecha_emision,
    )

    reglas = _REGLAS[tipo]
    senales: list[str] = []
    faltantes: list[str] = []
    score = 0
    exige_pades = tipo in TIPOS_PADES
    grupo = int(reglas.get("grupo", 2))
    perfil = str(reglas.get("perfil_pades") or tipo)

    alnum = contar_alnum(texto)
    if alnum >= MIN_TEXTO_ALNUM:
        score += 15
        senales.append("texto-real")
    else:
        faltantes.append("PDF con texto real extraíble (no escaneo/foto)")

    if exige_pades:
        if pades_ok:
            score += 20
            senales.append("pades-intacta")
            senales.append("emisor-oficial")
            senales.append("pades-trusted")
        else:
            faltantes.append(
                "firma electrónica avanzada PAdES íntegra y confiable (CA Chile)"
            )

    if contiene_alguna(texto, reglas["keywords"]):
        score += 20 if exige_pades else 30
        senales.append("palabra-clave")
        senales.append("tipo-ok")
    else:
        faltantes.append(f"texto típico de {reglas['label']}")

    if contiene_alguna(texto, reglas["emisores"]):
        score += 10
        senales.append("emisor")
    else:
        faltantes.append("emisor reconocible del documento")

    ruts = list(extraer_ruts(texto))
    rut = ruts[0] if ruts else None
    if rut:
        score += 10
        senales.append("rut-valido")
    else:
        faltantes.append("RUT de la empresa o del representante")

    fecha_emision = parsear_fecha_emision(texto)
    fechas = list(extraer_fechas(texto))
    if reglas.get("exige_fecha_reciente"):
        if fecha_dentro_ventana(fecha_emision):
            score += 10
            senales.append("fecha")
            senales.append("fecha-reciente")
        else:
            faltantes.append("fecha de emisión con menos de 60 días")
    elif fechas or fecha_emision:
        score += 10
        senales.append("fecha")
    else:
        faltantes.append("fecha del documento")

    glosa = detectar_glosa(texto, perfil) if exige_pades or tipo in TIPOS_PDF else None
    if exige_pades:
        if glosa:
            score += 5
            senales.append("glosa-estado")
        else:
            faltantes.append("glosa de estado esperada en el documento")

    if nombre_coincide(texto, nombre_empresa):
        score += 5
        senales.append("nombre-coincide")

    if rut and rut_empresa:
        try:
            perfil_rut = normalizar_rut(rut_empresa)
        except (RutInvalido, ValueError):
            perfil_rut = None
        if perfil_rut and perfil_rut in ruts:
            score += 10
            senales.append("rut-coincide-empresa")
        elif reglas.get("exige_rut_empresa"):
            faltantes.append("RUT del PDF debe coincidir con el RUT de la empresa")

    score = min(100, score)
    obl = set(_OBLIGATORIAS)
    if exige_pades:
        obl |= {
            "pades-intacta",
            "emisor-oficial",
            "pades-trusted",
            "glosa-estado",
        }
        if reglas.get("exige_fecha_reciente"):
            obl.add("fecha-reciente")
    tiene_obl = obl.issubset(senales)
    soporte = sum(1 for s in ("rut-valido", "fecha", "emisor") if s in senales)
    aceptado = score >= UMBRAL_ACEPTACION and tiene_obl and soporte >= 2
    if (
        reglas.get("exige_rut_empresa")
        and rut_empresa
        and "rut-coincide-empresa" not in senales
    ):
        aceptado = False

    if not aceptado:
        if "texto-real" not in senales:
            motivo = (
                "Solo se aceptan PDF con texto seleccionable. "
                "No se admiten fotos escaneadas ni PDF de solo imagen."
            )
        elif exige_pades and not pades_ok:
            motivo = (
                f"{reglas['label']} requiere firma PAdES íntegra, cobertura total "
                "y cadena de confianza a una CA acreditada de Chile."
            )
        elif faltantes:
            motivo = (
                f"No se pudo validar {reglas['label']} ({score}/100). Falta: "
                f"{', '.join(faltantes[:4])}."
            )
        else:
            motivo = f"No alcanza el umbral ({score}/100) para {reglas['label']}."
    else:
        extra = " con PAdES confiable" if exige_pades and pades_ok else ""
        motivo = f"{reglas['label']} válido{extra} ({score}/100)."

    return ResultadoDocEmpresa(
        aceptado=aceptado,
        score=score,
        tipo=tipo,
        senales=tuple(dict.fromkeys(senales)),
        motivo=motivo,
        rut_detectado=rut,
        verificado_criptograficamente=bool(exige_pades and pades_ok and aceptado),
        entidad_emisora=entidad_emisora if aceptado else None,
        fecha_emision=(
            fecha_emision.isoformat() if (aceptado and fecha_emision) else None
        ),
        sha256_hash=sha256_hash if aceptado else None,
        glosa=glosa if aceptado else None,
        grupo=grupo,
    )
