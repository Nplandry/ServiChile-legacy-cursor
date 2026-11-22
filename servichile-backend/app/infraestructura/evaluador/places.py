from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.dominio.transparencia.evaluador.ficha import (
    EvaluacionFicha,
    elegir_lugar_confiable,
    raiz_dominio,
    tokens_marca,
)
from app.infraestructura.evaluador.http_sync import enviar_json

class ClienteGooglePlaces:
    def __init__(self, api_key: str, *, base: str | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.base = (base or "https://places.googleapis.com/v1").rstrip("/")

    @property
    def configurado(self) -> bool:
        return bool(self.api_key)

    def _consultas(
        self,
        nombre: str | None,
        dominio: str,
        comuna: str | None,
        ciudad: str | None,
    ) -> list[str]:
        marca = (tokens_marca(nombre, dominio) or [raiz_dominio(dominio) or ""])[0]
        loc = " ".join(p for p in [comuna, ciudad] if p)
        queries: list[str] = [f"{dominio} Chile"]
        if marca and marca not in dominio:
            queries.append(f"{marca} {dominio} Chile")
        if nombre:
            queries.append(f'"{nombre}" {loc} Chile' if loc else f'"{nombre}" Chile')
        if marca and loc:
            queries.append(f"{marca} {loc} Chile")
        elif marca:
            queries.append(f"{marca} Chile")
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            qn = " ".join(q.split())
            if qn and qn not in seen:
                seen.add(qn)
                out.append(qn)
        return out[:2]

    def buscar_texto(
        self, query: str, *, tiempo_espera: float = 2.0, max_resultados: int = 3
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        if not self.configurado:
            return False, None, "GOOGLE_PLACES_API_KEY no configurado"
        url = f"{self.base}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.nationalPhoneNumber,places.websiteUri,places.rating,"
                "places.userRatingCount,places.regularOpeningHours,"
                "places.location,places.googleMapsUri"
            ),
        }
        carga = {
            "textQuery": query,
            "regionCode": "CL",
            "languageCode": "es",
            "maxResultCount": max_resultados,
        }
        return enviar_json(url, carga, headers=headers, tiempo_espera=tiempo_espera)

    def buscar_negocio(
        self,
        nombre: str | None,
        dominio: str,
        comuna: str | None = None,
        ciudad: str | None = None,
        *,
        tiempo_espera: float = 2.0,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        queries = self._consultas(nombre, dominio, comuna, ciudad)
        places: list[dict[str, Any]] = []
        errors: list[str] = []
        if queries:
            with ThreadPoolExecutor(max_workers=len(queries)) as pool:
                futs = [
                    pool.submit(
                        lambda q=q: self.buscar_texto(q, tiempo_espera=tiempo_espera)
                    )
                    for q in queries
                ]
                for fut in as_completed(futs):
                    ok, data, err = fut.result()
                    if ok and isinstance(data, dict):
                        places.extend(data.get("places") or [])
                    elif err:
                        errors.append(err)
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for p in places:
            key = str(p.get("id") or p.get("name") or id(p))
            if key in seen:
                continue
            seen.add(key)
            merged.append(p)
        lugar, evaluacion = elegir_lugar_confiable(
            merged,
            nombre_empresa=nombre,
            dominio=dominio,
            comuna=comuna,
            ciudad=ciudad,
        )
        carga: dict[str, Any] = {
            "ficha_assessment": evaluacion.a_dict(),
            "candidatos_considerados": len(merged),
        }
        if lugar is None or not evaluacion.confiable:
            if errors and not merged:
                carga["ficha_assessment"] = EvaluacionFicha(
                    confiable=False,
                    confianza=0.0,
                    puntaje_coincidencia=0,
                    razones=errors[:3],
                ).a_dict()
            return False, carga, "Sin ficha Places confiable"
        carga["place"] = lugar
        return True, carga, None
