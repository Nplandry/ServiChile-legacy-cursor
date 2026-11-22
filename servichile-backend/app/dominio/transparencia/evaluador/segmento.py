

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Segmento = Literal["b2b", "b2c", "unknown"]

B2B_PATTERNS = [
    r"\bb2b\b",
    r"industrial",
    r"industria",
    r"manufactur",
    r"minería",
    r"mineria",
    r"construcción",
    r"construccion",
    r"ingenier[ií]a",
    r"consultor[ií]a",
    r"software",
    r"saas",
    r"tecnolog[ií]a",
    r"inform[aá]tica",
    r"ti\b",
    r"enterprise",
    r"mayorista",
    r"proveedor\s+b2b",
    r"servicios?\s+profesionales",
    r"outsourcing",
    r"log[ií]stica\s+industrial",
    r"erp",
    r"desarrollo\s+de\s+software",
    r"gesti[oó]n\s+empresarial",
]

B2C_PATTERNS = [
    r"\bb2c\b",
    r"retail",
    r"e-?commerce",
    r"comercio\s+minorista",
    r"tienda",
    r"restaurante",
    r"cafeter[ií]a",
    r"food",
    r"delivery\s+consumidor",
    r"consumo\s+masivo",
    r"peluquer[ií]a",
    r"belleza",
    r"turismo",
    r"hospedaje",
    r"supermercado",
    r"moda",
    r"retail\s+local",
]

B2B_WEIGHT_MULTIPLIERS: dict[str, float] = {
    "fis_hours": 0.35,
    "fis_reviews": 0.65,
    "fis_rating": 0.75,
    "con_tyc": 1.45,
    "con_sla": 1.55,
    "con_dpa": 1.50,
    "con_clausulas": 1.45,
    "con_privacy": 1.20,
    "con_ley_21719": 1.25,
}

B2C_WEIGHT_MULTIPLIERS: dict[str, float] = {
    "fis_hours": 1.40,
    "fis_reviews": 1.25,
    "fis_rating": 1.20,
    "con_sla": 0.85,
    "con_dpa": 0.90,
}

@dataclass(frozen=True)
class PerfilSegmento:
    segmento: Segmento
    razon: str
    multiplicadores: dict[str, float]

def detectar_segmento(
    rubro: str | None = None,
    *,
    pista_segmento: str | None = None,
    nombre_empresa: str | None = None,
) -> PerfilSegmento:
    hint = (pista_segmento or "").strip().lower()
    if hint in {"b2b", "b2c"}:
        mult = B2B_WEIGHT_MULTIPLIERS if hint == "b2b" else B2C_WEIGHT_MULTIPLIERS
        return PerfilSegmento(
            segmento=hint, razon=f"hint explícito ({hint})", multiplicadores=mult
        )

    blob = f"{rubro or ''} {nombre_empresa or ''}".lower()
    b2b_hits = [p for p in B2B_PATTERNS if re.search(p, blob, re.I)]
    b2c_hits = [p for p in B2C_PATTERNS if re.search(p, blob, re.I)]

    if b2b_hits and not b2c_hits:
        return PerfilSegmento(
            segmento="b2b",
            razon=f"rubro/nombre B2B ({', '.join(b2b_hits[:3])})",
            multiplicadores=B2B_WEIGHT_MULTIPLIERS,
        )
    if b2c_hits and not b2b_hits:
        return PerfilSegmento(
            segmento="b2c",
            razon=f"rubro/nombre B2C ({', '.join(b2c_hits[:3])})",
            multiplicadores=B2C_WEIGHT_MULTIPLIERS,
        )
    if b2b_hits and b2c_hits:
        return PerfilSegmento(
            segmento="b2b",
            razon=f"señales mixtas; prioriza B2B ({', '.join(b2b_hits[:2])})",
            multiplicadores=B2B_WEIGHT_MULTIPLIERS,
        )
    return PerfilSegmento(
        segmento="unknown",
        razon="sin señal clara; pesos base",
        multiplicadores={},
    )

def peso_efectivo(
    peso_base: float, param_id: str, perfil: PerfilSegmento
) -> float:
    mult = perfil.multiplicadores.get(param_id, 1.0)
    return round(max(0.05, peso_base * mult), 3)
