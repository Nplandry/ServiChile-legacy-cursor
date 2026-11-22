

from __future__ import annotations

import logging

from app.dominio.puertos import VerificadorIdentidad
from app.infraestructura.evaluador.chilecompra import ClienteChileCompra

log = logging.getLogger(__name__)

class MuestraVerificadorRut:

    def existe_y_activo(self, rut: str) -> bool:
        return bool((rut or "").strip())

class EstrictoVerificadorRut:

    def existe_y_activo(self, rut: str) -> bool:
        return False

class ChileCompraVerificadorRut:

    def __init__(self, ticket: str, *, tiempo_espera: float = 3.0) -> None:
        self.cliente = ClienteChileCompra(ticket)
        self.tiempo_espera = tiempo_espera

    def existe_y_activo(self, rut: str) -> bool:
        if not (rut or "").strip():
            return False
        if not self.cliente.configurado:
            log.warning("ChileCompraVerificadorRut sin ticket; rechaza RUT.")
            return False
        ok, data, err = self.cliente.buscar_proveedor(rut, tiempo_espera=self.tiempo_espera)
        if not ok:
            log.info("ChileCompra RUT %s: %s", rut, err)
            return False
        codigo = ClienteChileCompra.codigo_desde(data if isinstance(data, dict) else None)
        return bool(codigo)

def construir_verificador_rut(
    nombre: str,
    *,
    app_env: str = "local",
    chilecompra_ticket: str = "",
) -> VerificadorIdentidad:
    modo = (nombre or "estricto").strip().lower()
    env = (app_env or "local").strip().lower()
    ticket = (chilecompra_ticket or "").strip()

    if modo == "muestra":
        if env == "test":
            return MuestraVerificadorRut()
        log.warning(
            "Verificador 'muestra' fuera de APP_ENV=test: se usa estricto "
            "(no se marca identidad solo por dígito verificador)."
        )
        return EstrictoVerificadorRut()

    if modo == "estricto":
        return EstrictoVerificadorRut()

    if modo == "chilecompra":
        return ChileCompraVerificadorRut(ticket)

    raise ValueError(f"Verificador de RUT desconocido: {nombre}")

