from __future__ import annotations

import re
from typing import Any

from app.infraestructura.evaluador.http_sync import obtener_json

def _format_rut_dots(rut: str) -> str:
    raw = (rut or "").strip().upper().replace(".", "").replace(" ", "")
    if "-" in raw:
        num, dv = raw.rsplit("-", 1)
    else:
        num, dv = raw[:-1], raw[-1]
    num = re.sub(r"\D", "", num)
    chunks: list[str] = []
    while num:
        chunks.append(num[-3:])
        num = num[:-3]
    return f"{'.'.join(reversed(chunks))}-{dv}"

class ClienteChileCompra:
    def __init__(self, ticket: str, *, base: str | None = None) -> None:
        self.ticket = (ticket or "").strip()
        self.base = (base or "https://api.mercadopublico.cl/servicios/v1").rstrip("/")

    @property
    def configurado(self) -> bool:
        return bool(self.ticket)

    def buscar_proveedor(
        self, rut: str, *, tiempo_espera: float = 2.0
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        if not self.configurado:
            return False, None, "CHILECOMPRA_TICKET no configurado"
        url = f"{self.base}/Publico/Empresas/BuscarProveedor"
        ok, data, err = obtener_json(
            url,
            params={"rutempresaproveedor": _format_rut_dots(rut), "ticket": self.ticket},
            tiempo_espera=tiempo_espera,
        )
        if not ok:
            return False, None, err
        return True, data if isinstance(data, dict) else {"raw": data}, None

    @staticmethod
    def codigo_desde(proveedor: dict[str, Any] | None) -> str | None:
        if not isinstance(proveedor, dict):
            return None
        for key in ("listaEmpresas", "Listado", "empresa", "Empresa"):
            node = proveedor.get(key)
            if isinstance(node, list) and node:
                return node[0].get("CodigoEmpresa") or node[0].get("Codigo")
            if isinstance(node, dict):
                return node.get("CodigoEmpresa") or node.get("Codigo")
        m = re.search(r"CodigoEmpresa['\":\s]+(\d+)", str(proveedor))
        return m.group(1) if m else None
