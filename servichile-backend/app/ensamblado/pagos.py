

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from functools import lru_cache

from sqlalchemy.orm import Session

from app.configuracion import obtener_configuracion
from app.infraestructura.correo_plataforma import EnviadorMemoria, EnviadorSmtp
from app.infraestructura.persistencia.modelos import obtener_sessionmaker
from app.infraestructura.persistencia.repositorios import (
    RepositorioCompraInforme,
    RepositorioCompraPublicacion,
    RepositorioCorreo,
    RepositorioNegocio,
    RepositorioUsuario,
)
from app.infraestructura.seguridad.jwt_reporte import JwtReporte
from app.infraestructura.transbank_webpay import (
    PasarelaWebpayHttp,
    PasarelaWebpayMemoria,
)
from app.servicios.pago_informe import ServicioPagoInforme
from app.servicios.pago_publicacion import ServicioPagoPublicacion
from app.servicios.radar_comercial import ServicioRadarComercial

log = logging.getLogger(__name__)

def permitir_pasarela_memoria() -> bool:

    if os.environ.get("SERVICHILE_ALLOW_MEMORIA_PASARELA") == "1":
        return True
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))

@lru_cache
def obtener_pasarela_webpay():
    settings = obtener_configuracion()
    if settings.app_env == "test":
        if permitir_pasarela_memoria():
            return PasarelaWebpayMemoria(autorizar=True)
        raise RuntimeError(
            "PasarelaWebpayMemoria solo en pytest o con "
            "SERVICHILE_ALLOW_MEMORIA_PASARELA=1. "
            "Use APP_ENV=local|production con Transbank real."
        )
    host = (settings.transbank_host or "").strip()
    commerce = (settings.transbank_commerce_code or "").strip()
    api_key = settings.transbank_api_key.get_secret_value().strip()
    test_key = (
        "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
    )
    if settings.app_env == "production":
        if (
            not host
            or not commerce
            or not api_key
            or "webpay3gint" in host.lower()
            or commerce == "597055555532"
            or api_key == test_key
        ):
            raise RuntimeError(
                "Pasarela Webpay: credenciales de producción incompletas o de TEST."
            )
    return PasarelaWebpayHttp(
        commerce_code=commerce,
        api_key=api_key,
        host=host,
    )

def _enviador():
    settings = obtener_configuracion()
    if settings.app_env == "test":
        return EnviadorMemoria(simular=True)
    if not settings.smtp_host.strip() or not settings.smtp_desde.strip():
        return EnviadorMemoria(simular=False)
    return EnviadorSmtp(
        settings.smtp_host.strip(),
        settings.smtp_port,
        settings.smtp_usuario.strip(),
        settings.smtp_clave.get_secret_value(),
        settings.smtp_desde.strip(),
        starttls=settings.smtp_starttls,
    )

def armar_servicio_pago(session: Session) -> ServicioPagoInforme:
    settings = obtener_configuracion()
    retorno = (settings.public_frontend_url or "").strip()
    if retorno and "pago=retorno" not in retorno:
        sep = "&" if "?" in retorno else "?"
        retorno = f"{retorno}{sep}pago=retorno"
    usuarios = RepositorioUsuario(session)
    radar = ServicioRadarComercial(
        RepositorioNegocio(session),
        usuarios,
        RepositorioCorreo(session),
        _enviador(),
        JwtReporte(
            settings.jwt_secret.get_secret_value(), settings.reporte_expires_minutes
        ),
    )
    from app.dominio.pago_informe import PRECIO_INFORME_CLP

    return ServicioPagoInforme(
        RepositorioCompraInforme(session),
        RepositorioNegocio(session),
        obtener_pasarela_webpay(),
        radar,
        return_url=retorno,
        reclamo_email=settings.pagos_reclamo_email,
        reclamo_whatsapp=settings.pagos_reclamo_whatsapp,
        monto=PRECIO_INFORME_CLP,
        origenes_permitidos=list(settings.cors_origins or []),
        print_secret=settings.secreto_print_token(),
        usuarios=usuarios,
    )

def armar_servicio_publicacion(session: Session) -> ServicioPagoPublicacion:
    settings = obtener_configuracion()
    retorno = (settings.public_frontend_url or "").strip()
    if retorno and "pago=retorno" not in retorno:
        sep = "&" if "?" in retorno else "?"
        retorno = f"{retorno}{sep}pago=retorno"
    if retorno and "producto=publicacion" not in retorno:
        retorno = f"{retorno}&producto=publicacion"
    from app.dominio.pago_publicacion import PRECIO_PUBLICACION_CLP

    return ServicioPagoPublicacion(
        RepositorioCompraPublicacion(session),
        obtener_pasarela_webpay(),
        return_url=retorno,
        reclamo_email=settings.pagos_reclamo_email,
        reclamo_whatsapp=settings.pagos_reclamo_whatsapp,
        monto=PRECIO_PUBLICACION_CLP,
        origenes_permitidos=list(settings.cors_origins or []),
        usuarios=RepositorioUsuario(session),
        enviador=_enviador(),
    )

def _reconciliar_lote() -> int:
    settings = obtener_configuracion()
    SesionLocal = obtener_sessionmaker()
    with SesionLocal() as session:
        n_inf = armar_servicio_pago(session).reconciliar_pendientes(
            min_edad_seg=int(settings.pagos_reconciliar_min_edad_seg),
            max_edad_seg=7200,
            limite=25,
        )
        n_pub = armar_servicio_publicacion(session).reconciliar_pendientes(
            min_edad_seg=int(settings.pagos_reconciliar_min_edad_seg),
            max_edad_seg=7200,
            limite=25,
        )
        return int(n_inf) + int(n_pub)

async def bucle_reconciliar_pagos(stop: asyncio.Event) -> None:
    from app.ensamblado import pagos_estado

    config = obtener_configuracion()
    segundos = float(config.pagos_reconciliar_seconds or 0)
    if config.app_env == "test" or segundos <= 0:
        pagos_estado.marcar_activo(False)
        log.info(
            "Reconciliación Webpay desactivada (env=%s, segundos=%s).",
            config.app_env,
            segundos,
        )
        return

    intervalo = max(60.0, segundos)
    pagos_estado.marcar_activo(True)
    log.info(
        "Reconciliación Webpay cada %.0f s (min edad %s s).",
        intervalo,
        config.pagos_reconciliar_min_edad_seg,
    )

    while not stop.is_set():
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=intervalo)
        if stop.is_set():
            break
        try:
            n = await asyncio.to_thread(_reconciliar_lote)
            pagos_estado.marcar_exito(n)
            if n:
                log.info("Reconciliación Webpay: %s compras cerradas.", n)
        except Exception as e:
            pagos_estado.marcar_error(str(e))
            log.exception("Reconciliación Webpay falló.")
