

from __future__ import annotations

import logging
import os

from sqlalchemy import text

from app.configuracion import Configuracion
from app.infraestructura.trust_vault import (
    obtener_contexto_validacion,
    ruta_ca_default,
)

log = logging.getLogger(__name__)

_FKS_COMPRAS = (
    "compras_informe_usuario_id_fkey",
    "compras_informe_business_id_fkey",
)

_FKS_COMPRAS_PUBLICACION = (
    "compras_publicacion_usuario_id_fkey",
    "compras_publicacion_business_id_fkey",
)

_CLOUD_MARKERS = (
    "K_SERVICE",
    "RENDER",
    "FLY_APP_NAME",
    "RAILWAY_ENVIRONMENT",
    "DYNO",
    "ECS_CONTAINER_METADATA_URI",
    "KUBERNETES_SERVICE_HOST",
)

def precargar_pades_ca(config: Configuracion) -> None:

    try:
        obtener_contexto_validacion(str(config.pades_ca_ruta()))
    except Exception:
        try:
            obtener_contexto_validacion(str(ruta_ca_default()))
        except Exception:
            log.warning(
                "No se pudo precargar ca_chile.pem; se intentará en la primera validación PAdES."
            )

def verificar_fks_compras_informe(config: Configuracion) -> None:

    if config.app_env != "production":
        return
    url = (config.database_url or "").lower()
    if "sqlite" in url:
        return
    try:
        from app.infraestructura.persistencia.modelos import obtener_motor

        with obtener_motor().connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conname IN "
                    "('compras_informe_usuario_id_fkey', "
                    "'compras_informe_business_id_fkey')"
                )
            ).fetchall()
            idx = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE indexname = 'uq_compras_informe_autorizada' "
                    "LIMIT 1"
                )
            ).fetchone()
        halladas = {r[0] for r in rows}
        faltan = [n for n in _FKS_COMPRAS if n not in halladas]
        if faltan:
            raise RuntimeError(
                "Faltan FKs de compras_informe en production: "
                + ", ".join(faltan)
                + ". Aplique db/migrations/047–048 como owner "
                "(GRANT REFERENCES si hace falta)."
            )
        if idx is None:
            raise RuntimeError(
                "Falta índice uq_compras_informe_autorizada. "
                "Aplique db/migrations/049_compras_informe_unica_autorizada.sql."
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "No se pudieron verificar FKs/índice de compras_informe "
            "en production: " + str(exc)
        ) from exc

def verificar_compras_publicacion(config: Configuracion) -> None:

    if config.app_env != "production":
        return
    url = (config.database_url or "").lower()
    if "sqlite" in url:
        return
    try:
        from app.infraestructura.persistencia.modelos import obtener_motor

        with obtener_motor().connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conname IN "
                    "('compras_publicacion_usuario_id_fkey', "
                    "'compras_publicacion_business_id_fkey')"
                )
            ).fetchall()
            idx = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE indexname = 'uq_compras_publicacion_cupon_libre' "
                    "LIMIT 1"
                )
            ).fetchone()
            tabla = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'compras_publicacion' LIMIT 1"
                )
            ).fetchone()
        if tabla is None:
            raise RuntimeError(
                "Falta tabla compras_publicacion. "
                "Aplique db/migrations/050_compras_publicacion.sql."
            )
        halladas = {r[0] for r in rows}
        faltan = [n for n in _FKS_COMPRAS_PUBLICACION if n not in halladas]
        if faltan:
            raise RuntimeError(
                "Faltan FKs de compras_publicacion en production: "
                + ", ".join(faltan)
                + ". Aplique db/migrations/051_compras_publicacion_fks.sql "
                "como owner (GRANT REFERENCES si hace falta)."
            )
        if idx is None:
            raise RuntimeError(
                "Falta índice uq_compras_publicacion_cupon_libre. "
                "Aplique db/migrations/050_compras_publicacion.sql."
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "No se pudieron verificar FKs/índice de compras_publicacion "
            "en production: " + str(exc)
        ) from exc

def _database_parece_remota(database_url: str) -> bool:
    u = (database_url or "").lower()
    if not u or "sqlite" in u:
        return False

    for local in ("localhost", "127.0.0.1", "::1", "@db:", "@postgres:"):
        if local in u:
            return False
    return "@" in u

def verificar_entorno_produccion(config: Configuracion) -> None:

    if os.environ.get("SERVICHILE_ALLOW_MEMORIA_PASARELA") == "1" and config.app_env == "production":
        raise RuntimeError(
            "SERVICHILE_ALLOW_MEMORIA_PASARELA no está permitido con "
            "APP_ENV=production."
        )
    if config.app_env == "production":
        return
    if (
        os.environ.get("SERVICHILE_REQUIRE_PRODUCTION") == "1"
        or os.environ.get("SERVICHILE_DEPLOY") == "1"
    ):
        raise RuntimeError(
            "SERVICHILE_REQUIRE_PRODUCTION/SERVICHILE_DEPLOY=1 exige "
            "APP_ENV=production."
        )
    presentes = [k for k in _CLOUD_MARKERS if os.environ.get(k)]
    if presentes:
        raise RuntimeError(
            "Entorno cloud detectado ("
            + ", ".join(presentes)
            + f") pero APP_ENV={config.app_env}. "
            "Configure APP_ENV=production."
        )

    if _database_parece_remota(config.database_url):
        raise RuntimeError(
            "DATABASE_URL parece remota pero APP_ENV="
            f"{config.app_env}. Use APP_ENV=production o "
            "SERVICHILE_DEPLOY=1 en el playbook de VPS."
        )

def verificar_redis(config: Configuracion) -> None:

    if config.app_env == "test":
        return
    url = (config.redis_url or "").strip()
    if not url:
        raise RuntimeError(
            "REDIS_URL ausente. Ejemplo local: redis://localhost:6379/0"
        )
    try:
        from app.infraestructura.redis_cliente import ping_redis

        ping_redis(url)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "No se pudo conectar a REDIS_URL: " + str(exc)
        ) from exc
