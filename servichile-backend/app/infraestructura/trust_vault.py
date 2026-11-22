

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_CA = (
    Path(__file__).resolve().parent / "certs" / "ca_chile.pem"
)

def ruta_ca_default() -> Path:
    return _DEFAULT_CA

@lru_cache(maxsize=8)
def cargar_certificados(pem_path: str) -> tuple:
    from pyhanko.keys import load_certs_from_pemder

    path = Path(pem_path)
    if not path.is_file():
        raise FileNotFoundError(f"Bóveda CA no encontrada: {path}")
    certs = tuple(load_certs_from_pemder([str(path)]))
    if not certs:
        raise RuntimeError(f"Bóveda CA vacía: {path}")
    logger.info("Bóveda CA cargada: %s (%d certificados)", path, len(certs))
    return certs

@lru_cache(maxsize=8)
def obtener_contexto_validacion(pem_path: str):

    from pyhanko_certvalidator import ValidationContext

    roots = list(cargar_certificados(pem_path))
    return ValidationContext(
        trust_roots=roots,
        allow_fetching=False,
        revocation_mode="soft-fail",
    )

def invalidar_cache_confianza() -> None:
    cargar_certificados.cache_clear()
    obtener_contexto_validacion.cache_clear()
