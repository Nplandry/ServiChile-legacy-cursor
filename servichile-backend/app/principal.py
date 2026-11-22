import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import autenticacion, negocios, pagos, perfil, radar, reporte, trabajos

from app.configuracion import obtener_configuracion
from app.ensamblado.arranque import (
    precargar_pades_ca,
    verificar_compras_publicacion,
    verificar_entorno_produccion,
    verificar_fks_compras_informe,
    verificar_redis,
)
from app.ensamblado.evaluador import bucle_evaluador
from app.ensamblado.pagos import bucle_reconciliar_pagos

settings = obtener_configuracion()
verificar_entorno_produccion(settings)
precargar_pades_ca(settings)
verificar_fks_compras_informe(settings)
verificar_compras_publicacion(settings)
verificar_redis(settings)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    from contextlib import suppress

    stop = asyncio.Event()
    tareas: list[asyncio.Task] = []
    if settings.run_background_jobs:
        tareas.append(
            asyncio.create_task(
                bucle_evaluador(stop), name="evaluador-segundo-plano"
            )
        )
        tareas.append(
            asyncio.create_task(
                bucle_reconciliar_pagos(stop), name="pagos-reconciliar-tbk"
            )
        )
    else:
        logging.getLogger(__name__).info(
            "Bucles de fondo desactivados (RUN_BACKGROUND_JOBS=false)."
        )
    try:
        yield
    finally:
        stop.set()
        for tarea in tareas:
            tarea.cancel()
            with suppress(asyncio.CancelledError):
                await tarea

app = FastAPI(
    title="ServiChile API",
    version="0.1.0",
    description="Autenticación, marketplace B2B, Índice de Transparencia y reporte verificable.",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=800)

app.include_router(autenticacion.router)

app.include_router(perfil.router)

app.include_router(negocios.router)

app.include_router(trabajos.router)

app.include_router(trabajos.titular_router)

app.include_router(reporte.router)
app.include_router(radar.router_radar)
app.include_router(pagos.router)
_RUTAS_SILENCIOSAS = ("GET / ", "GET /json/version ")

class _FiltroAccessSilencioso(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:

        msg = record.getMessage()

        return not any((ruta in msg for ruta in _RUTAS_SILENCIOSAS))

logging.getLogger("uvicorn.access").addFilter(_FiltroAccessSilencioso())

@app.get("/", include_in_schema=False)
def raiz() -> dict[str, str]:

    return {"estado": "ok"}

@app.get("/json/version", include_in_schema=False)
def json_version() -> dict[str, str]:

    return {
        "Browser": "ServiChile",
        "Protocol-Version": "1.0",
        "webSocketDebuggerUrl": "",
    }

@app.get("/salud", tags=["Sistema"])
def salud() -> dict:
    from sqlalchemy import text

    from app.ensamblado import evaluador_estado, pagos_estado
    from app.infraestructura.persistencia.modelos import obtener_motor

    ev = evaluador_estado.snapshot()
    pg = pagos_estado.snapshot()
    deps: dict[str, str] = {}

    if settings.app_env == "test":
        deps["redis"] = "omitido"
        deps["postgres"] = "omitido"
    else:
        url = (settings.redis_url or "").strip()
        try:
            from app.infraestructura.redis_cliente import ping_redis

            ping_redis(url)
            deps["redis"] = "ok"
        except Exception as exc:
            deps["redis"] = "error:" + type(exc).__name__
        try:
            with obtener_motor().connect() as conn:
                conn.execute(text("SELECT 1"))
            deps["postgres"] = "ok"
        except Exception as exc:
            deps["postgres"] = "error:" + type(exc).__name__

    ok = (
        bool(ev.get("ok", True))
        and bool(pg.get("ok", True))
        and deps.get("redis") in ("ok", "omitido")
        and deps.get("postgres") in ("ok", "omitido")
    )
    smtp_ok = bool(
        (settings.smtp_host or "").strip() and (settings.smtp_desde or "").strip()
    )
    deps["smtp"] = "configurado" if smtp_ok else "omitido"

    return {
        "estado": "ok" if ok else "degradado",
        "dependencias": deps,
        "evaluador": ev,
        "pagos_reconciliar": pg,
        "background_jobs": bool(settings.run_background_jobs),
    }

@app.exception_handler(StarletteHTTPException)
async def manejador_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:

    detalle = exc.detail
    if exc.status_code == 404 and detalle in (None, "Not Found"):
        path = request.url.path
        detalle = (
            f"Ruta no encontrada: {path}. "
            "Compruebe el path o use /docs para ver el contrato /v1."
        )
        if settings.app_env == "production":
            detalle = (
                f"Ruta no encontrada: {path}. "
                "Compruebe el path o la documentación de la API."
            )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detalle},
        headers=getattr(exc, "headers", None) or None,
    )
