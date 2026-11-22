

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.dominio.rut import normalizar_rut, RutInvalido

AVAL_MAX_BYTES = 8 * 1024 * 1024
UMBRAL_ACEPTACION = 70

MIN_TEXTO_ALNUM = 120

TipoAval = Literal["carta_aval", "boleta", "poliza", "otro"]

_OBLIGATORIAS = frozenset({"texto-real", "palabra-clave"})

_PALABRAS_CLAVE = (
    "avalista",
    "aval",
    "garantia",
    "boletadegarantia",
    "boleta de garantia",
    "poliza",
    "fianza",
    "respaldo",
)

_EMISORES = (
    "banco",
    "bancaria",
    "bancario",
    "companiade seguros",
    "compania de seguros",
    "seguros",
    "aseguradora",
    "notaria",
    "notario",
    "corredora",
    "institucion financiera",
)

@dataclass(frozen=True)
class ResultadoAval:
    aceptado: bool
    score: int
    tipo: TipoAval
    senales: tuple[str, ...]
    motivo: str
    rut_detectado: str | None = None
    monto_detectado: str | None = None

def _sin_acentos(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

def _compact(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _sin_acentos(texto).lower())

def _texto_lower(texto: str) -> str:
    return _sin_acentos(texto or "").lower()

def clasificar_tipo(texto: str) -> TipoAval:

    t = _texto_lower(texto)
    c = _compact(texto)
    if "boletadegarantia" in c or "boleta de garantia" in t or (
        "boleta" in t and "garantia" in t
    ):
        return "boleta"
    if "poliza" in c or "poliza de garantia" in t or "poliza de seguro" in t:
        return "poliza"
    if (
        "avalista" in c
        or "cartadeaval" in c
        or "carta de aval" in t
        or re.search(r"\baval\b", t)
    ):
        return "carta_aval"
    if any(k.replace(" ", "") in c or k in t for k in ("garantia", "fianza", "respaldo")):
        return "carta_aval"
    return "otro"

def _tiene_palabra_clave(texto: str) -> bool:
    t = _texto_lower(texto)
    c = _compact(texto)
    for kw in _PALABRAS_CLAVE:
        k = _sin_acentos(kw).lower()
        if " " in k:
            if k in t:
                return True
        elif k in c or re.search(rf"\b{re.escape(k)}\b", t):
            return True
    return False

def _extraer_ruts(texto: str) -> list[str]:
    encontrados: list[str] = []
    vistos: set[str] = set()
    for m in re.finditer(
        r"\b(\d{1,2}\.?\d{3}\.?\d{3})\s*-\s*([0-9Kk])\b", texto or ""
    ):
        raw = f"{m.group(1)}-{m.group(2).upper()}"
        try:
            norm = normalizar_rut(raw)
        except (RutInvalido, ValueError):
            continue
        if norm not in vistos:
            vistos.add(norm)
            encontrados.append(norm)
    return encontrados

def _extraer_montos(texto: str) -> list[str]:
    out: list[str] = []
    patrones = (
        r"(?:\$|CLP|UF|U\.F\.)\s*[\d]{1,3}(?:[.\s]\d{3})*(?:,\d+)?",
        r"(?:\$|CLP)\s*\d{4,}",
        r"\bUF\s*[\d]+(?:[.,]\d+)?\b",
        r"\bmonto\s*(?:de\s*)?(?:\$|CLP|UF)?\s*[\d]{1,3}(?:[.\s]\d{3})*",
    )
    for pat in patrones:
        for m in re.finditer(pat, texto or "", re.I):
            out.append(m.group(0).strip())
    return out

def _extraer_fechas(texto: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto or ""
    ):
        out.append(m.group(0))
    for m in re.finditer(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
        texto or "",
        re.I,
    ):
        out.append(m.group(0))
    return out

def _tiene_emisor(texto: str) -> bool:
    t = _texto_lower(texto)
    c = _compact(texto)
    for e in _EMISORES:
        if e.replace(" ", "") in c or e in t:
            return True
    return False

def _tokens_nombre(nombre: str) -> set[str]:
    limpio = re.sub(r"[^a-záéíóúñ\s]", " ", _sin_acentos(nombre).lower())
    return {t for t in limpio.split() if len(t) >= 2}

def _nombre_coincide(texto: str, nombre_perfil: str | None) -> bool:
    if not nombre_perfil:
        return False
    tokens = _tokens_nombre(nombre_perfil)
    if not tokens:
        return False
    t = _texto_lower(texto)
    hits = sum(1 for tok in tokens if tok in t)
    return hits >= min(2, len(tokens))

def validar_aval(
    *,
    texto: str,
    rut_perfil: str | None = None,
    nombre_perfil: str | None = None,
) -> ResultadoAval:
    senales: list[str] = []
    faltantes: list[str] = []
    score = 0

    alnum = sum(1 for ch in (texto or "") if ch.isalnum())
    if alnum >= MIN_TEXTO_ALNUM:
        score += 15
        senales.append("texto-real")
    else:
        faltantes.append("PDF con texto real extraíble (no escaneo/foto)")

    if _tiene_palabra_clave(texto):
        score += 25
        senales.append("palabra-clave")
    else:
        faltantes.append(
            "palabra clave (aval, avalista, garantía, boleta, póliza, fianza o respaldo)"
        )

    tipo = clasificar_tipo(texto)
    if tipo != "otro":
        score += 10
        senales.append(f"tipo-{tipo}")
    else:
        senales.append("tipo-otro")

    ruts = _extraer_ruts(texto)
    rut = ruts[0] if ruts else None
    if rut:
        score += 15
        senales.append("rut-valido")
    else:
        faltantes.append("RUT del titular o avalista")

    montos = _extraer_montos(texto)
    monto = montos[0] if montos else None
    if monto:
        score += 10
        senales.append("monto")
    else:
        faltantes.append("monto o UF/$")

    fechas = _extraer_fechas(texto)
    if fechas:
        score += 10
        senales.append("fecha")
    else:
        faltantes.append("fecha del documento")

    emisor_ok = _tiene_emisor(texto)
    if emisor_ok:
        score += 15
        senales.append("emisor")
    else:
        faltantes.append("emisor (banco, seguros o notaría)")

    if _nombre_coincide(texto, nombre_perfil):
        score += 10
        senales.append("nombre-coincide")

    if rut and rut_perfil:
        try:
            perfil_norm = normalizar_rut(rut_perfil)
        except (RutInvalido, ValueError):
            perfil_norm = None
        if perfil_norm and perfil_norm in ruts:
            score += 10
            senales.append("rut-coincide-perfil")

    score = min(100, score)
    tiene_obligatorias = _OBLIGATORIAS.issubset(senales)

    soporte = sum(
        1
        for s in ("rut-valido", "monto", "fecha", "emisor")
        if s in senales
    )
    aceptado = (
        score >= UMBRAL_ACEPTACION
        and tiene_obligatorias
        and soporte >= 2
        and tipo != "otro"
    )

    if not aceptado:
        if "texto-real" not in senales:
            motivo = (
                "Solo se aceptan PDF con texto seleccionable. "
                "No se admiten fotos escaneadas ni PDF de solo imagen."
            )
        elif tipo == "otro" and "palabra-clave" in senales:
            motivo = (
                f"Se detectaron palabras de respaldo pero no se pudo clasificar "
                f"como carta de aval, boleta o póliza ({score}/100)."
            )
        elif faltantes:
            motivo = (
                f"No se pudo validar el aval/garantía ({score}/100). Falta: "
                f"{', '.join(faltantes[:4])}."
            )
        else:
            motivo = (
                f"No alcanza el umbral ({score}/100). "
                "Suba un PDF textual de aval, boleta de garantía o póliza."
            )
    else:
        motivo = f"Aval/garantía válido ({tipo}, {score}/100)."

    return ResultadoAval(
        aceptado=aceptado,
        score=score,
        tipo=tipo,
        senales=tuple(dict.fromkeys(senales)),
        motivo=motivo,
        rut_detectado=rut,
        monto_detectado=monto,
    )
