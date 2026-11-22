

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from functools import lru_cache

from sqlalchemy.orm import Session

from app.configuracion import obtener_configuracion
from app.dominio.puertos import AnalizadorDocEmpresa
from app.infraestructura.geocodificacion import construir_geocodificador
from app.infraestructura.persistencia.modelos import obtener_sessionmaker
from app.infraestructura.persistencia.repositorios import RepositorioNegocio
from app.infraestructura.evaluador.adaptador import AdaptadorEvaluador, ConfiguracionEvaluador
from app.servicios.negocio import ServicioNegocio

log = logging.getLogger(__name__)

@lru_cache
def obtener_adaptador_evaluador() -> AdaptadorEvaluador:
    s = obtener_configuracion()
    return AdaptadorEvaluador(
        ConfiguracionEvaluador(
            app_env=s.app_env,
            chilecompra_ticket=s.chilecompra_ticket,
            google_places_api_key=s.google_places_api_key,
            presupuesto_segundos=s.rater_budget_seconds,
        )
    )

def armar_servicio_negocio(
    session: Session,
    analizador_docs: AnalizadorDocEmpresa | None = None,
) -> ServicioNegocio:

    from app.infraestructura.persistencia.repositorios import RepositorioTrabajo

    return ServicioNegocio(
        RepositorioNegocio(session),
        analizador_docs,
        obtener_adaptador_evaluador(),
        construir_geocodificador(obtener_configuracion().app_env),
        RepositorioTrabajo(session),
    )

def _cache_lecturas():
    from app.infraestructura.cache_respuesta import construir_cache_respuesta

    cfg = obtener_configuracion()
    return construir_cache_respuesta(cfg.redis_url, activo=cfg.app_env != "test")

def _invalidar_cache_lecturas() -> None:
    try:
        from app.infraestructura.cache_respuesta import invalidar_lecturas_publicas

        invalidar_lecturas_publicas(_cache_lecturas())
    except Exception:
        log.exception("No se pudo invalidar caché tras el evaluador.")

def _invalidar_cache_negocio(negocio_id) -> None:
    try:
        from app.infraestructura.cache_respuesta import invalidar_negocio

        invalidar_negocio(_cache_lecturas(), negocio_id)
    except Exception:
        log.exception("No se pudo invalidar caché del negocio %s.", negocio_id)

def _refrescar_lote() -> int:
    SesionLocal = obtener_sessionmaker()
    with SesionLocal() as session:
        n = armar_servicio_negocio(session).refrescar_evaluador_todos()
    if n > 0:
        _invalidar_cache_lecturas()
    return n

def refrescar_evaluador_negocio(negocio_id) -> None:

    from uuid import UUID

    bid = negocio_id if isinstance(negocio_id, UUID) else UUID(str(negocio_id))
    SesionLocal = obtener_sessionmaker()
    with SesionLocal() as session:
        try:

            armar_servicio_negocio(session).refrescar_evaluador(bid)
            _invalidar_cache_negocio(bid)
        except Exception:
            session.rollback()
            log.exception("Evaluador diferido falló para negocio %s", bid)

def encolar_evaluador(
    tareas_segundo_plano, negocio_id, *, servicio: ServicioNegocio | None = None
):

    from app.servicios.negocio_reputacion import a_titular

    if obtener_configuracion().app_env == "test":
        if servicio is None:
            raise RuntimeError("encolar_evaluador en test requiere servicio")
        return a_titular(servicio.refrescar_evaluador(negocio_id))
    tareas_segundo_plano.add_task(refrescar_evaluador_negocio, negocio_id)
    return None

async def bucle_evaluador(stop: asyncio.Event) -> None:
    config = obtener_configuracion()
    minutos = float(config.rater_refresh_minutes or 0)
    if config.app_env == "test" or minutos <= 0:
        log.info(
            "Evaluador en segundo plano desactivado (env=%s, minutos=%s).",
            config.app_env,
            minutos,
        )
        return

    intervalo = max(60.0, minutos * 60.0)
    log.info("Evaluador en segundo plano cada %.0f min.", minutos)

    from app.ensamblado import evaluador_estado

    try:
        n = await asyncio.to_thread(_refrescar_lote)
        evaluador_estado.marcar_exito(n)
        log.info("Evaluador en segundo plano inicial: %s empresas.", n)
    except Exception as e:
        evaluador_estado.marcar_error(str(e))
        log.exception("Evaluador en segundo plano: fallo en arranque inicial.")

    while not stop.is_set():
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=intervalo)
        if stop.is_set():
            break
        try:
            n = await asyncio.to_thread(_refrescar_lote)
            evaluador_estado.marcar_exito(n)
            log.info("Evaluador en segundo plano: %s empresas refrescadas.", n)
        except Exception as e:
            evaluador_estado.marcar_error(str(e))
            log.exception("Evaluador en segundo plano falló.")
