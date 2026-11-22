from __future__ import annotations

import re

from dataclasses import dataclass

from datetime import datetime

UMBRAL_ACEPTACION = 70

ANTECEDENTES_MAX_BYTES = 8 * 1024 * 1024

_OBLIGATORIAS = frozenset(
    {
        "formato-srcei",
        "itext",
        "folio-etiquetado",
        "codigo-etiquetado",
        "run-etiquetado",
        "seccion-condenas",
        "texto-real",
        "pades-intacta",
        "emisor-oficial",
        "pades-trusted",
        "fecha-reciente",
        "glosa-estado",
    }
)

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
class ResultadoAntecedentes:

    aceptado: bool

    score: int

    anotaciones: bool | None

    folio: str | None

    codigo: str | None

    run: str | None

    senales: tuple[str, ...]

    motivo: str

    verificado_criptograficamente: bool = False

    entidad_emisora: str | None = None

    fecha_emision: str | None = None

    sha256_hash: str | None = None

    glosa: str | None = None

def digito_verificador(cuerpo: str) -> str:

    s = 0

    m = 2

    for d in reversed(cuerpo):

        s += int(d) * m

        m = 2 if m == 7 else m + 1

    r = 11 - s % 11

    if r == 11:

        return "0"

    if r == 10:

        return "K"

    return str(r)

def run_valido(run: str) -> bool:

    limpio = re.sub("[^0-9Kk]", "", run or "")

    if len(limpio) < 2:

        return False

    cuerpo, dv = (limpio[:-1], limpio[-1].upper())

    if not cuerpo.isdigit():

        return False

    return digito_verificador(cuerpo) == dv

def _compact(texto: str) -> str:

    return re.sub("[^a-z0-9]", "", (texto or "").lower())

def detectar_anotaciones(texto: str) -> bool | None:

    compact = _compact(texto)

    if not compact or "certificadodeantecedentes" not in compact:

        return None

    if "sinantecedentes" in compact:

        return False

    if (
        "registrogeneraldecondenas" in compact
        or "registroespecialdecondenas" in compact
    ):

        return True

    return None

def _extraer_folio(texto: str) -> str | None:

    m = re.search("FOLIO\\s*:\\s*([0-9]{10,14})", texto, re.I)

    return m.group(1) if m else None

def _extraer_codigo(texto: str) -> str | None:

    m = re.search(
        "C[oó]digo\\s*(?:de\\s*)?Verificaci[oó]n\\s*:?\\s*([0-9a-fA-F]{8,16})",
        texto,
        re.I,
    )

    return m.group(1).lower() if m else None

def _extraer_run(texto: str) -> str | None:

    m = re.search(
        "R\\.?U\\.?N\\.?\\s*:?\\s*([0-9]{1,2}\\.?[0-9]{3}\\.?[0-9]{3}\\s*-\\s*[0-9Kk])",
        texto,
        re.I,
    )

    if m:

        return re.sub("\\s+", "", m.group(1))

    return None

def _fecha_emision_texto(texto: str) -> datetime | None:

    m = re.search(
        "FECHA\\s*EMISI[OÓ]N\\s*:?\\s*(\\d{1,2})\\s+([A-Za-zÁÉÍÓÚáéíóú]+)\\s+(\\d{4})\\s*,?\\s*(\\d{1,2}):(\\d{2})",
        texto,
        re.I | re.S,
    )

    if not m:

        m = re.search(
            "(\\d{1,2})\\s+(Noviembre|noviembre|Enero|enero|Febrero|febrero|Marzo|marzo|Abril|abril|Mayo|mayo|Junio|junio|Julio|julio|Agosto|agosto|Septiembre|septiembre|Octubre|octubre|Diciembre|diciembre)\\s+(\\d{4})\\s*,?\\s*(\\d{1,2}):(\\d{2})",
            texto,
        )

    if not m:

        return None

    dia, mes_txt, anio, hora, minuto = m.groups()

    mes = _MESES.get(mes_txt.lower())

    if not mes:

        return None

    try:

        return datetime(int(anio), mes, int(dia), int(hora), int(minuto))

    except ValueError:

        return None

def _nombre_coherente(nombre: str | None, folio: str | None, run: str | None) -> bool:

    if not nombre or not folio or (not run):

        return False

    base = nombre.rsplit("/", 1)[-1]

    cuerpo_run = re.sub("[^0-9]", "", run)[:-1]

    patron = re.compile(f"^ANT_{re.escape(folio)}_{re.escape(cuerpo_run)}\\.pdf$", re.I)

    return bool(patron.match(base))

def validar_certificado_antecedentes(
    *,
    nombre_archivo: str | None = None,
    meta_creation: datetime | None = None,
    producer: str | None = None,
    num_paginas: int = 0,
    texto: str = "",
    texto_real: bool = False,
    pades_ok: bool = False,
    entidad_emisora: str | None = None,
    sha256_hash: str | None = None,
) -> ResultadoAntecedentes:

    from app.dominio.pades import (
        detectar_glosa,
        fecha_dentro_ventana,
        parsear_fecha_emision,
    )

    senales: list[str] = []

    score = 0

    faltantes: list[str] = []

    if texto_real:

        score += 10

        senales.append("texto-real")

    else:

        faltantes.append("PDF con texto real seleccionable (no escaneo)")

    if pades_ok:

        score += 15

        senales.append("pades-intacta")

        senales.append("emisor-oficial")

        senales.append("pades-trusted")

    else:

        faltantes.append(
            "firma PAdES íntegra, cobertura total y confiable (CA Chile)"
        )

    if num_paginas != 1:

        faltantes.append("debe tener exactamente 1 página")

    else:

        score += 5

        senales.append("una-pagina")

    prod = (producer or "").lower()

    if "itext" in prod:

        score += 10

        senales.append("itext")

    else:

        faltantes.append("producer iText (típico SRCeI)")

    texto_l = texto or ""

    compact = _compact(texto_l)

    es_srcei = (
        "registrocivileidentificacion" in compact
        or ("registrocivil" in compact and "republicadechile" in compact)
    ) and "certificadodeantecedentes" in compact

    if es_srcei:

        score += 15

        senales.append("formato-srcei")

    else:

        faltantes.append("texto de Certificado de Antecedentes del Registro Civil")

    if "finesparticulares" in compact or "finosespeciales" in compact:

        score += 5

        senales.append("fines")

    if "registrogeneraldecondenas" in compact:

        score += 5

        senales.append("seccion-condenas")

    else:

        faltantes.append("sección Registro General de Condenas")

    if "firmaelectronica" in compact or "timbreelectronico" in compact:

        score += 5

        senales.append("firma-electronica")

    folio = _extraer_folio(texto_l)

    if folio:

        score += 5

        senales.append("folio-etiquetado")

    else:

        faltantes.append("FOLIO: etiquetado")

    codigo = _extraer_codigo(texto_l)

    if codigo:

        score += 5

        senales.append("codigo-etiquetado")

    else:

        faltantes.append("Código Verificación etiquetado")

    run = _extraer_run(texto_l)

    if run and run_valido(run):

        score += 5

        senales.append("run-etiquetado")

    else:

        faltantes.append("R.U.N. etiquetado con DV válido")

        run = run if run and run_valido(run) else None

    fecha_txt = _fecha_emision_texto(texto_l)
    fecha_emision = parsear_fecha_emision(texto_l)
    if fecha_txt and fecha_emision is None:
        fecha_emision = fecha_txt.date()

    if fecha_dentro_ventana(fecha_emision):

        score += 10

        senales.append("fecha-reciente")

    else:

        faltantes.append("fecha de emisión con menos de 60 días")

    if fecha_txt and meta_creation:

        delta = abs(
            (
                fecha_txt.replace(tzinfo=None) - meta_creation.replace(tzinfo=None)
            ).total_seconds()
        )

        if delta <= 180:

            score += 5

            senales.append("fecha-meta")

    elif fecha_txt:

        score += 2

        senales.append("fecha-texto")

    glosa = detectar_glosa(texto_l, "antecedentes")

    if glosa:

        score += 5

        senales.append("glosa-estado")

    else:

        faltantes.append("glosa de estado (ej. Sin antecedentes / Sin anotaciones)")

    if _nombre_coherente(nombre_archivo, folio, run):

        score += 5

        senales.append("nombre-archivo")

    score = min(100, score)

    tiene_obligatorias = _OBLIGATORIAS.issubset(senales)

    anotaciones = detectar_anotaciones(texto_l) if es_srcei else None

    aceptado = (
        score >= UMBRAL_ACEPTACION and tiene_obligatorias and (anotaciones is not None)
    )

    if not aceptado:

        if not texto_real:

            motivo = (
                "Solo se aceptan PDF con texto seleccionable. "
                "No se admiten fotos escaneadas ni PDF de solo imagen."
            )

        elif not pades_ok:

            motivo = (
                "El certificado debe traer firma electrónica avanzada (PAdES) "
                "íntegra del Registro Civil / Acepta. No edite el PDF."
            )

        elif es_srcei and anotaciones is None:

            motivo = "El PDF parece un certificado, pero no se pudo determinar si tiene o no anotaciones. Suba el PDF oficial completo."

        elif faltantes:

            motivo = f"No es un certificado de antecedentes válido ({score}/100). Falta: {', '.join(faltantes[:4])}."

        else:

            motivo = f"No alcanza el umbral de validación ({score}/100). Use el PDF oficial descargado de registrocivil.gob.cl."

    elif anotaciones:

        motivo = (
            "Certificado válido con firma PAdES íntegra. "
            "Anotaciones: Sí (no afecta el puntaje)."
        )

    else:

        motivo = (
            "Certificado válido con firma PAdES íntegra. "
            "Anotaciones: No (no afecta el puntaje)."
        )

    return ResultadoAntecedentes(
        aceptado=aceptado,
        score=score,
        anotaciones=anotaciones if aceptado else None,
        folio=folio,
        codigo=codigo,
        run=run,
        senales=tuple(senales),
        motivo=motivo,
        verificado_criptograficamente=bool(pades_ok and aceptado),
        entidad_emisora=entidad_emisora if aceptado else None,
        fecha_emision=fecha_emision.isoformat() if (aceptado and fecha_emision) else None,
        sha256_hash=sha256_hash if aceptado else None,
        glosa=glosa if aceptado else None,
    )
