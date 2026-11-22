

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.dominio.entidades import Negocio
from app.dominio.transparencia.evaluador.fijos import hints_fijos
from app.dominio.transparencia.evaluador.motor import (
    ResultadoEvaluador,
    bloquear_fisica,
    construir_puntajes,
)
from app.dominio.transparencia.evaluador.parametros import IDS_ESTADO, IDS_FISICA, IDS_SITIO
from app.infraestructura.evaluador import cache_lugares
from app.infraestructura.evaluador.chilecompra import ClienteChileCompra
from app.infraestructura.evaluador.places import ClienteGooglePlaces
from app.infraestructura.evaluador.rastreador_web import dominio_de_url, rastrear_sitio

@dataclass(frozen=True, slots=True)
class ConfiguracionEvaluador:

    app_env: str = "local"
    chilecompra_ticket: str = ""
    google_places_api_key: str = ""
    presupuesto_segundos: float = 2.0

def _es_test(app_env: str) -> bool:
    return (app_env or "").strip().lower() == "test"

def _places_limite_cuota(err: str | None, data: Any) -> bool:
    partes = [str(err or "")]
    if isinstance(data, dict):
        evaluacion = data.get("ficha_assessment") or {}
        razones = evaluacion.get("razones") or evaluacion.get("reasons") or []
        partes.extend(str(r) for r in razones)
    blob = " ".join(partes)
    return "429" in blob

def _simular_fuente_con_key(*, app_env: str, configurado: bool) -> bool:

    if _es_test(app_env):
        return True
    return not configurado

def _aplicar_fijos(
    pistas: dict[str, float],
    fuentes: dict[str, str],
    estados: dict[str, str],
    ids: tuple[str, ...] | list[str],
    *,
    fuente: str = "fijos",
) -> None:
    tabla = hints_fijos()
    for pid in ids:
        pistas[pid] = tabla[pid]
        fuentes[pid] = fuente
        estados[pid] = "ok"

def _comuna_ciudad(direccion: str | None) -> tuple[str | None, str | None]:
    if not direccion or not direccion.strip():
        return None, None
    partes = [p.strip() for p in re.split(r",|\|", direccion) if p.strip()]
    if not partes:
        return None, None
    if len(partes) == 1:
        return partes[0], partes[0]
    return partes[-2] if len(partes) >= 2 else partes[0], partes[-1]

def _aplicar_ceros_por_campos(
    pistas: dict[str, float],
    estados: dict[str, str],
    evidencia: dict[str, str],
    negocio: Negocio,
) -> None:

    if not (negocio.direccion or "").strip():
        pistas["fis_address"] = 0.0
        estados["fis_address"] = "ok"
        evidencia.pop("fis_address", None)
    if not (negocio.telefono or "").strip():
        pistas["fis_phone"] = 0.0
        estados["fis_phone"] = "ok"
        evidencia.pop("fis_phone", None)
    if not (negocio.rut_empresa or "").strip():
        for pid in IDS_ESTADO:
            pistas[pid] = 0.0
            estados[pid] = "ok"
            evidencia.pop(pid, None)
    if not (negocio.sitio_web or "").strip():
        for pid in IDS_SITIO:
            pistas[pid] = 0.0
            estados[pid] = "ok"
            evidencia.pop(pid, None)

def _nombre_proveedor(prov: dict[str, Any] | None) -> str | None:
    if not isinstance(prov, dict):
        return None
    lista = prov.get("listaEmpresas") or prov.get("Listado") or []
    if isinstance(lista, list) and lista and isinstance(lista[0], dict):
        nombre = lista[0].get("NombreEmpresa")
        return str(nombre) if nombre else None
    return None

def _confiable_ficha(evaluacion: dict[str, Any]) -> bool:
    if "confiable" in evaluacion:
        return bool(evaluacion.get("confiable"))
    return bool(evaluacion.get("reliable"))

def _coincidencia_dominio(evaluacion: dict[str, Any]) -> bool:
    if "coincidencia_dominio" in evaluacion:
        return bool(evaluacion.get("coincidencia_dominio"))
    return bool(evaluacion.get("domain_match"))

class AdaptadorEvaluador:

    def __init__(self, config: ConfiguracionEvaluador) -> None:
        self.config = config
        self.places = ClienteGooglePlaces(config.google_places_api_key)
        self.chilecompra = ClienteChileCompra(config.chilecompra_ticket)

    def evaluar(self, negocio: Negocio) -> ResultadoEvaluador:
        pistas: dict[str, float] = {}
        evidencia: dict[str, str] = {}
        fuentes: dict[str, str] = {}
        estados: dict[str, str] = {}
        meta: dict = {"modo": "produccion", "app_env": self.config.app_env}
        tiempo_espera = max(
            0.5, min(float(self.config.presupuesto_segundos or 2.0), 8.0)
        )
        ficha_fiable: bool | None = None

        dominio = dominio_de_url(negocio.sitio_web) or ""
        nombre = negocio.nombre
        comuna, ciudad = _comuna_ciudad(negocio.direccion)
        tiene_sitio = bool((negocio.sitio_web or "").strip())
        tiene_rut = bool((negocio.rut_empresa or "").strip())

        rastreador_fijos = tiene_sitio and _es_test(self.config.app_env)
        places_fijos = _simular_fuente_con_key(
            app_env=self.config.app_env,
            configurado=self.places.configurado,
        )
        cc_fijos = _simular_fuente_con_key(
            app_env=self.config.app_env,
            configurado=self.chilecompra.configurado,
        )

        if not tiene_sitio:
            meta["rastreador_web"] = {"omitido": True, "razon": "sin sitio_web"}
        elif rastreador_fijos:
            _aplicar_fijos(pistas, fuentes, estados, IDS_SITIO)
            meta["rastreador_web"] = {"modo": "fijos"}

        puede_places = bool(dominio) or bool((nombre or "").strip())
        if places_fijos:
            _aplicar_fijos(pistas, fuentes, estados, IDS_FISICA)
            ficha_fiable = True
            meta["places"] = {
                "modo": "fijos",
                "configurado": self.places.configurado,
            }
        elif not puede_places:
            bloquear_fisica(
                pistas,
                evidencia,
                fuentes,
                estados,
                motivo="Sin nombre ni sitio web para Places",
            )
            ficha_fiable = False
            meta["places"] = {"omitido": True}

        if not tiene_rut:
            for pid in IDS_ESTADO:
                pistas[pid] = 0.0
                estados[pid] = "ok"
                evidencia.pop(pid, None)
                fuentes[pid] = "ficha"
            meta["chilecompra"] = {"omitido": True, "razon": "sin rut"}
        elif cc_fijos:
            _aplicar_fijos(pistas, fuentes, estados, IDS_ESTADO)
            meta["chilecompra"] = {
                "modo": "fijos",
                "configurado": self.chilecompra.configurado,
            }

        need_rastreador = tiene_sitio and not rastreador_fijos
        need_places = (not places_fijos) and puede_places
        need_cc = tiene_rut and not cc_fijos

        rastreador_out: dict[str, Any] | None = None
        places_out: tuple[bool, dict[str, Any] | None, str | None] | None = None
        cc_out: tuple[bool, dict[str, Any] | None, str | None] | None = None

        jobs: dict[str, Any] = {}
        if need_rastreador:
            jobs["rastreador_web"] = lambda: rastrear_sitio(
                negocio.sitio_web or "", tiempo_espera=tiempo_espera
            )
        if need_places:
            jobs["places"] = lambda: self.places.buscar_negocio(
                nombre, dominio, comuna, ciudad, tiempo_espera=tiempo_espera
            )
        if need_cc:
            jobs["chilecompra"] = lambda: self.chilecompra.buscar_proveedor(
                negocio.rut_empresa or "", tiempo_espera=tiempo_espera
            )

        if jobs:
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                futures = {key: pool.submit(fn) for key, fn in jobs.items()}
                if "rastreador_web" in futures:
                    rastreador_out = futures["rastreador_web"].result()
                if "places" in futures:
                    places_out = futures["places"].result()
                if "chilecompra" in futures:
                    cc_out = futures["chilecompra"].result()

        if rastreador_out is not None:
            pistas_rastreador = rastreador_out.get("pistas_puntaje") or {}
            paginas = int(rastreador_out.get("paginas_escaneadas") or 0)
            hallazgos = int(rastreador_out.get("hallazgos_count") or 0)
            https_ok = float(pistas_rastreador.get("cyb_https") or 0) >= 50
            web_ok = float(pistas_rastreador.get("dig_website") or 0) >= 50
            rastreador_fallido = (
                paginas <= 0 or not pistas_rastreador or not (https_ok or web_ok)
            )
            if rastreador_fallido:
                meta["rastreador_web"] = {
                    "modo": "fallido",
                    "paginas_escaneadas": paginas,
                    "hallazgos": hallazgos,
                }
            else:
                pistas.update(pistas_rastreador)
                for pid in pistas_rastreador:
                    fuentes[pid] = "rastreador_web"
                    estados[pid] = "ok"

                rutas = rastreador_out.get("rutas_evidencia") or {}
                if isinstance(rutas, dict):
                    for pid, ruta in rutas.items():
                        key = str(pid or "").strip()
                        val = str(ruta or "").strip()
                        if key.startswith("con_") and val.startswith("/"):
                            evidencia[key] = val
                meta["rastreador_web"] = {
                    "paginas_escaneadas": paginas,
                    "hallazgos": hallazgos,
                    "rutas": {
                        k: v
                        for k, v in (rutas.items() if isinstance(rutas, dict) else [])
                        if str(k).startswith("con_")
                    },
                }
        elif need_rastreador:
            meta["rastreador_web"] = {"modo": "fallido", "razon": "sin_respuesta"}

        if places_out is not None:
            ok, data, err = places_out
            if _places_limite_cuota(err, data):
                en_almacen = cache_lugares.obtener(dominio) if dominio else None
                if isinstance(en_almacen, dict) and en_almacen.get("place"):
                    ficha_fiable = self._aplicar_places(
                        en_almacen, pistas, evidencia, fuentes, estados, meta
                    )
                    meta["places"] = {
                        "modo": "almacen",
                        "error": err,
                        "razon": "429; snapshot Places en caché",
                    }
                else:
                    razones = []
                    if isinstance(data, dict):
                        evaluacion = data.get("ficha_assessment") or {}
                        razones = evaluacion.get("razones") or evaluacion.get("reasons") or []
                    meta["places"] = {
                        "modo": "limite_cuota",
                        "error": err,
                        "razones": razones[:3],
                    }
                    meta["places_error"] = err or "Places rate limit (429)"
            else:
                ficha_fiable = self._aplicar_places(
                    data if ok else data, pistas, evidencia, fuentes, estados, meta
                )
                if (
                    ficha_fiable
                    and dominio
                    and isinstance(data, dict)
                    and data.get("place")
                ):
                    cache_lugares.guardar(dominio, data)
                if err:
                    meta["places_error"] = err

        if cc_out is not None:
            ok, prov, err = cc_out
            codigo = ClienteChileCompra.codigo_desde(prov) if ok else None
            inscrito = bool(codigo)
            pistas["est_proveedor"] = 100.0 if inscrito else 0.0
            if inscrito:
                nombre_prov = _nombre_proveedor(prov if isinstance(prov, dict) else None)
                ev = f"Código {codigo}"
                if nombre_prov:
                    ev += f" · {nombre_prov}"
                    marca = (negocio.nombre or "").strip().lower()
                    if marca and nombre_prov.strip().lower() not in marca and marca not in nombre_prov.strip().lower():
                        ev += " (razón social ≠ nombre ficha)"
                evidencia["est_proveedor"] = ev
            else:
                evidencia["est_proveedor"] = err or "No inscrito en Mercado Público"
            for pid in IDS_ESTADO:
                fuentes[pid] = "chilecompra"
                estados[pid] = "ok"
            meta["chilecompra"] = {"ok": ok, "codigo": codigo, "error": err}

        _aplicar_ceros_por_campos(pistas, estados, evidencia, negocio)

        return construir_puntajes(
            pistas=pistas,
            mapa_evidencia=evidencia,
            mapa_fuentes=fuentes,
            mapa_estados=estados,
            rubro=negocio.categoria,
            nombre_empresa=nombre,
            ficha_fiable=ficha_fiable,
            resumen=(
                f"Evaluador de {nombre}"
                + (f" ({dominio})" if dominio else "")
                + f". Señales: {len([k for k, v in pistas.items() if v is not None])}."
            ),
            recomendaciones=self._recomendaciones(pistas),
            metadatos=meta,
        )

    def _aplicar_places(
        self, data, pistas, evidencia, fuentes, estados, meta
    ) -> bool | None:
        if not isinstance(data, dict):
            bloquear_fisica(
                pistas, evidencia, fuentes, estados, motivo="Places no disponible"
            )
            return False
        evaluacion = data.get("ficha_assessment") or {}
        meta["ficha_assessment"] = evaluacion
        place = data.get("place") if isinstance(data.get("place"), dict) else None
        confiable = _confiable_ficha(evaluacion) if evaluacion else bool(place)
        if not confiable or not place:
            razones = evaluacion.get("razones") or evaluacion.get("reasons") or []
            motivo = "; ".join(razones) or "Sin ficha confiable"
            bloquear_fisica(pistas, evidencia, fuentes, estados, motivo=motivo)
            return False
        pistas["fis_places_exists"] = 100.0
        place_name = (
            ((place.get("displayName") or {}).get("text") if isinstance(place.get("displayName"), dict) else None)
            or evaluacion.get("nombre_lugar")
            or evaluacion.get("place_name")
            or ""
        )
        evidencia["fis_places_exists"] = (
            f"Places: {place_name}" if place_name else "Ficha Google confiable"
        )
        rating = place.get("rating")
        if isinstance(rating, (int, float)):
            pistas["fis_rating"] = min(100.0, (float(rating) / 5.0) * 100.0)
            evidencia["fis_rating"] = f"{rating}/5"
        else:
            pistas["fis_rating"] = 40.0
        count = place.get("userRatingCount") or 0
        pistas["fis_reviews"] = min(100.0, 20.0 + float(count) * 2.0)
        evidencia["fis_reviews"] = f"{count} reseñas"
        pistas["fis_address"] = 95.0 if place.get("formattedAddress") else 20.0
        evidencia["fis_address"] = place.get("formattedAddress") or ""
        pistas["fis_phone"] = 95.0 if place.get("nationalPhoneNumber") else 20.0
        evidencia["fis_phone"] = place.get("nationalPhoneNumber") or ""
        pistas["fis_hours"] = 90.0 if place.get("regularOpeningHours") else 30.0
        if place.get("regularOpeningHours"):
            evidencia["fis_hours"] = "Horario publicado en Google"
        if place.get("websiteUri") and _coincidencia_dominio(evaluacion):
            pistas["dig_website"] = max(pistas.get("dig_website", 0), 100.0)
            evidencia["dig_website"] = place["websiteUri"]
        for pid in IDS_FISICA:
            fuentes[pid] = "google_places"
            estados[pid] = "ok"
        return True

    @staticmethod
    def _recomendaciones(pistas: dict[str, float]) -> list[str]:
        recs: list[str] = []
        if pistas.get("con_privacy", 0) < 50:
            recs.append("Publicar Política de Privacidad accesible.")
        if pistas.get("con_ley_21719", 0) < 50:
            recs.append("Incorporar referencias a la Ley 21.719.")
        if pistas.get("fis_places_exists", 0) < 50:
            recs.append("Crear/verificar ficha Google Business Profile.")
        if pistas.get("est_proveedor", 0) <= 0:
            recs.append("Completar RUT de empresa para cruzar Mercado Público.")
        return recs[:6]
