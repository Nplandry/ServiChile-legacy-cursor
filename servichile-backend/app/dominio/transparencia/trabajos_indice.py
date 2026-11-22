

from __future__ import annotations

from app.dominio.entidades import ObservableSenal

ID_TRABAJOS_CONCRETADOS = "trabajos_concretados"
GRUPO_PLATAFORMA = "plataforma"

_CAP_CONCRETADOS = 10

def pct_trabajos_concretados(cantidad: int) -> int:
    n = max(0, int(cantidad or 0))
    return int(min(100, round(100.0 * n / _CAP_CONCRETADOS)))

def observable_trabajos_concretados(cantidad: int) -> ObservableSenal:
    n = max(0, int(cantidad or 0))
    pct = pct_trabajos_concretados(n)
    detalle = (
        f"{n} trabajo cerrado con QR en ServiChile."
        if n == 1
        else f"{n} trabajos cerrados con QR en ServiChile."
    )
    return ObservableSenal(
        id=ID_TRABAJOS_CONCRETADOS,
        etiqueta="Trabajos Concretados en ServiChile",
        detalle=detalle,
        score=pct,
        peso="1.5",
        grupo=GRUPO_PLATAFORMA,
        razones=[],
    )

def es_observable_trabajos(oid: str) -> bool:
    return str(oid or "") == ID_TRABAJOS_CONCRETADOS
