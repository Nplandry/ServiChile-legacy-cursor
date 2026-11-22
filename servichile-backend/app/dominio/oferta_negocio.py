

from __future__ import annotations

import re
from dataclasses import dataclass

INDUSTRIAS = (
    "mineria",
    "retail",
    "salud",
    "construccion",
    "tecnologia",
    "sector-publico",
)
CONTRATACIONES = (
    "cotizacion-directa",
    "contrato-recurrente",
    "licitacion-oc",
    "factura-electronica",
)
MONTOS = ("bajo", "medio", "alto")
PLAZOS = ("menos-2h", "en-el-dia", "24-48h")

CONCRETADOS = ("1", "5", "10")

MAX_SERVICIOS = 6
MAX_REFERENCIAS = 8
MAX_LARGO_SERVICIO = 40
MAX_LARGO_REFERENCIA = 80

_ESPACIOS = re.compile(r"\s+")
_ETIQUETA = re.compile(
    r"^[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ][0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ .,&'’/\-]*$"
)

class OfertaInvalida(ValueError):
    def __init__(self, mensaje: str) -> None:
        self.mensaje = mensaje
        super().__init__(mensaje)

@dataclass(frozen=True)
class FiltroListado:
    categoria: str | None = None
    q: str | None = None
    industria: str | None = None
    contratacion: str | None = None
    monto: str | None = None
    plazo: str | None = None
    concretados_min: int | None = None

def normalizar_etiquetas(
    valores: list[str] | tuple[str, ...] | None,
    *,
    max_items: int,
    max_len: int,
) -> tuple[str, ...]:
    if valores is None:
        return ()
    if not isinstance(valores, (list, tuple)):
        raise OfertaInvalida("El listado de etiquetas no es válido.")
    if len(valores) > max_items:
        raise OfertaInvalida(f"Puede indicar hasta {max_items} etiquetas.")
    vistos: set[str] = set()
    salida: list[str] = []
    for crudo in valores:
        if not isinstance(crudo, str):
            raise OfertaInvalida("Cada etiqueta debe ser texto.")
        texto = _ESPACIOS.sub(" ", crudo).strip()
        if not texto:
            continue
        if len(texto) < 2 or len(texto) > max_len:
            raise OfertaInvalida(
                f"Cada etiqueta debe tener entre 2 y {max_len} caracteres."
            )
        if not _ETIQUETA.match(texto):
            raise OfertaInvalida("Use solo letras, números y los signos . , & ' / -")
        clave = texto.casefold()
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(texto)
    return tuple(salida)

def normalizar_catalogo(
    valores: list[str] | tuple[str, ...] | None,
    permitidos: frozenset[str],
    *,
    etiqueta: str,
) -> tuple[str, ...]:
    if valores is None:
        return ()
    if not isinstance(valores, (list, tuple)):
        raise OfertaInvalida(f"{etiqueta} no es válido.")
    salida: list[str] = []
    for item in valores:
        if not isinstance(item, str) or item not in permitidos:
            raise OfertaInvalida(f"{etiqueta} incluye un valor no permitido.")
        if item not in salida:
            salida.append(item)
    return tuple(salida)

def normalizar_opcion(
    valor: str | None, permitidos: frozenset[str], *, etiqueta: str
) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise OfertaInvalida(f"{etiqueta} no es válido.")
    texto = valor.strip()
    if not texto:
        return None
    if texto not in permitidos:
        raise OfertaInvalida(f"{etiqueta} no es válido.")
    return texto

def servicios_de(valores) -> tuple[str, ...]:
    return normalizar_etiquetas(
        valores, max_items=MAX_SERVICIOS, max_len=MAX_LARGO_SERVICIO
    )

def referencias_de(valores) -> tuple[str, ...]:
    return normalizar_etiquetas(
        valores, max_items=MAX_REFERENCIAS, max_len=MAX_LARGO_REFERENCIA
    )

def industrias_de(valores) -> tuple[str, ...]:
    return normalizar_catalogo(valores, frozenset(INDUSTRIAS), etiqueta="Industrias")

def contrataciones_de(valores) -> tuple[str, ...]:
    return normalizar_catalogo(
        valores, frozenset(CONTRATACIONES), etiqueta="Cómo se contrata"
    )

def monto_de(valor) -> str | None:
    return normalizar_opcion(valor, frozenset(MONTOS), etiqueta="Monto")

def plazo_de(valor) -> str | None:
    return normalizar_opcion(valor, frozenset(PLAZOS), etiqueta="Plazo")

def concretados_de(valor) -> str | None:
    return normalizar_opcion(
        valor, frozenset(CONCRETADOS), etiqueta="Trabajos concretados"
    )

def concretados_minimo(valor: str | None) -> int | None:
    opcion = concretados_de(valor)
    if opcion is None:
        return None
    return int(opcion)
