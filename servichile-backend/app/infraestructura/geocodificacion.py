

from __future__ import annotations

import hashlib
import logging
import re
from typing import Protocol

from app.infraestructura.evaluador.http_sync import obtener_json

log = logging.getLogger(__name__)

_UA = "ServiChile/1.0 (transparencia-b2b; contacto@servichile.local)"

class Geocodificador(Protocol):
    def geocodificar(self, direccion: str) -> tuple[float, float] | None: ...

class GeocodificadorNulo:
    def geocodificar(self, direccion: str) -> tuple[float, float] | None:
        return None

class GeocodificadorDeterminista:

    def geocodificar(self, direccion: str) -> tuple[float, float] | None:
        texto = (direccion or "").strip()
        if len(texto) < 3:
            return None
        digest = hashlib.sha256(texto.casefold().encode()).hexdigest()
        n = int(digest[:8], 16)
        lat = -33.45 + ((n % 2000) - 1000) * 0.0001
        lng = -70.66 + (((n // 2000) % 2000) - 1000) * 0.0001
        return round(lat, 6), round(lng, 6)

class GeocodificadorNominatim:

    def __init__(self, *, tiempo_espera: float = 4.0) -> None:
        self.tiempo_espera = tiempo_espera
        self.base = "https://nominatim.openstreetmap.org/search"

    def geocodificar(self, direccion: str) -> tuple[float, float] | None:
        texto = re.sub(r"\s+", " ", (direccion or "").strip())
        if len(texto) < 3:
            return None
        q = texto if re.search(r"chile", texto, re.I) else f"{texto}, Chile"
        ok, data, err = obtener_json(
            self.base,
            params={
                "q": q,
                "format": "json",
                "limit": 1,
                "countrycodes": "cl",
                "addressdetails": 0,
            },
            headers={"User-Agent": _UA, "Accept-Language": "es-CL,es"},
            tiempo_espera=self.tiempo_espera,
        )
        if not ok or not isinstance(data, list) or not data:
            log.info(
                "Geocodificación falló para %r: %s", texto[:80], err or "sin resultados"
            )
            return None
        hit = data[0] if isinstance(data[0], dict) else None
        if not hit:
            return None
        try:
            lat = float(hit["lat"])
            lng = float(hit["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        if not (-56.0 <= lat <= -17.0 and -76.0 <= lng <= -66.0):
            log.info("Geocodificación fuera de Chile descartada: %s,%s", lat, lng)
            return None
        return round(lat, 6), round(lng, 6)

def construir_geocodificador(app_env: str) -> Geocodificador:
    env = (app_env or "local").strip().lower()
    if env == "test":
        return GeocodificadorDeterminista()
    return GeocodificadorNominatim()

