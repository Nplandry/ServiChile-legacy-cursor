

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencias import (
    LimiteSolicitudesDep,
    ServicioPagoInformeDep,
    ServicioRadarDep,
    UsuarioActualDep,
    demasiadas_solicitudes,
)
from app.api.esquemas.radar import InformeSalida
from app.dominio.errores import InformeSinCompra, NegocioNoEncontrado

router_radar = APIRouter(prefix="/v1/businesses", tags=["Radar"])

_NO_ENCONTRADO = "Negocio no encontrado."
_SIN_COMPRA = "Debe comprar el informe de proveedor para acceder."

@router_radar.post(
    "/{business_id}/informe-riesgo",
    response_model=InformeSalida,
)
def informe_riesgo(
    business_id: uuid.UUID,
    usuario: UsuarioActualDep,
    servicio: ServicioRadarDep,
    pagos: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"informe:{usuario.id}", 10):
        raise demasiadas_solicitudes()
    try:
        pagos.exigir_acceso_informe(usuario, business_id)
        resultado = servicio.informe(usuario, business_id)
    except NegocioNoEncontrado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, _NO_ENCONTRADO) from None
    except InformeSinCompra as e:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {"mensaje": e.mensaje, "codigo": e.codigo},
        ) from None
    return InformeSalida(
        enviado=resultado.enviado,
        destino=resultado.destino,
        qr_payload=resultado.qr_payload,
        expires_at=resultado.qr_expira,
    )
