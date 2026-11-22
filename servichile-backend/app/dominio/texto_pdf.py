

from __future__ import annotations

import re
import unicodedata

from app.dominio.rut import RutInvalido, normalizar_rut

MIN_TEXTO_ALNUM = 120
PDF_MAX_BYTES = 8 * 1024 * 1024

def sin_acentos(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

def compact(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", sin_acentos(texto).lower())

def texto_lower(texto: str) -> str:
    return sin_acentos(texto or "").lower()

def contar_alnum(texto: str) -> int:
    return sum(1 for ch in (texto or "") if ch.isalnum())

def extraer_ruts(texto: str) -> list[str]:
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

def extraer_montos(texto: str) -> list[str]:
    out: list[str] = []
    patrones = (
        r"(?:\$|CLP|UF|U\.F\.)\s*[\d]{1,3}(?:[.\s]\d{3})*(?:,\d+)?",
        r"(?:\$|CLP)\s*\d{4,}",
        r"\bUF\s*[\d]+(?:[.,]\d+)?\b",
    )
    for pat in patrones:
        for m in re.finditer(pat, texto or "", re.I):
            out.append(m.group(0).strip())
    return out

def extraer_fechas(texto: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto or ""):
        out.append(m.group(0))
    for m in re.finditer(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
        r"septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b",
        texto or "",
        re.I,
    ):
        out.append(m.group(0))
    return out

def tokens_nombre(nombre: str) -> set[str]:
    limpio = re.sub(r"[^a-záéíóúñ\s]", " ", sin_acentos(nombre).lower())
    return {t for t in limpio.split() if len(t) >= 2}

def nombre_coincide(texto: str, nombre: str | None) -> bool:
    if not nombre:
        return False
    toks = tokens_nombre(nombre)
    if not toks:
        return False
    t = texto_lower(texto)
    hits = sum(1 for tok in toks if tok in t)
    return hits >= min(2, len(toks))

def contiene_alguna(texto: str, claves: tuple[str, ...]) -> bool:
    t = texto_lower(texto)
    c = compact(texto)
    for kw in claves:
        k = sin_acentos(kw).lower()
        if " " in k:
            if k in t:
                return True
        elif k in c or re.search(rf"\b{re.escape(k)}\b", t):
            return True
    return False
