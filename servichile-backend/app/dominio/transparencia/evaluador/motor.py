

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.dominio.entidades import ObservableSenal
from app.dominio.transparencia.evaluador.parametros import (
    GRUPO_FE,
    PARAMETROS,
    CategoriaEvaluador,
    nota_desde_puntaje,
)
from app.dominio.transparencia.evaluador.segmento import (
    PerfilSegmento,
    detectar_segmento,
    peso_efectivo,
)

_ESTADOS_NO_MEDIDOS = {"omitido", "sin_puntaje", "error", "faltante"}

def _acotar(v: float) -> float:
    return max(0.0, min(100.0, float(v)))

@dataclass(frozen=True, slots=True)
class PuntajeParametro:
    id: str
    nombre: str
    categoria: CategoriaEvaluador
    puntaje: float | None
    peso: float
    evidencia: str | None = None
    fuente: str | None = None
    estado: str = "ok"

@dataclass(frozen=True, slots=True)
class PuntajeCategoria:
    categoria: CategoriaEvaluador
    puntaje: float | None
    puntuado: bool
    parametros: tuple[PuntajeParametro, ...]

@dataclass
class ResultadoEvaluador:
    puntaje_global: float | None
    nota: str | None
    categorias: list[PuntajeCategoria]
    parametros: list[PuntajeParametro]
    ficha_fiable: bool | None = None
    resumen: str | None = None
    recomendaciones: list[str] = field(default_factory=list)
    metadatos: dict = field(default_factory=dict)

    def a_observables(self) -> list[ObservableSenal]:

        out: list[ObservableSenal] = []
        for p in self.parametros:
            if p.estado in _ESTADOS_NO_MEDIDOS or p.puntaje is None:
                continue
            puntaje = int(round(_acotar(p.puntaje)))
            detalle = (p.evidencia or "").strip()

            if p.id.startswith("con_") and detalle.startswith("/"):
                pass
            elif p.fuente and detalle:
                detalle = f"{detalle} · {p.fuente}"
            elif p.fuente and not detalle:
                detalle = p.fuente
            out.append(
                ObservableSenal(
                    id=p.id,
                    etiqueta=p.nombre,
                    detalle=detalle,
                    score=puntaje,
                    peso=f"{p.peso:.1f}",
                    grupo=GRUPO_FE.get(p.categoria, "operativa"),
                    razones=[],
                )
            )
        return out

def construir_puntajes(
    *,
    pistas: dict[str, float],
    mapa_evidencia: dict[str, str] | None = None,
    mapa_fuentes: dict[str, str] | None = None,
    mapa_estados: dict[str, str] | None = None,
    rubro: str | None = None,
    nombre_empresa: str | None = None,
    pista_segmento: str | None = None,
    ficha_fiable: bool | None = None,
    resumen: str | None = None,
    recomendaciones: list[str] | None = None,
    metadatos: dict | None = None,
) -> ResultadoEvaluador:
    mapa_evidencia = mapa_evidencia or {}
    mapa_fuentes = mapa_fuentes or {}
    mapa_estados = mapa_estados or {}
    perfil = detectar_segmento(
        rubro, pista_segmento=pista_segmento, nombre_empresa=nombre_empresa
    )

    params: list[PuntajeParametro] = []
    for pdef in PARAMETROS:
        estado = mapa_estados.get(pdef.id)
        raw = pistas.get(pdef.id)
        peso = peso_efectivo(pdef.peso, pdef.id, perfil)
        if estado in {"omitido", "sin_puntaje", "error"}:
            params.append(
                PuntajeParametro(
                    id=pdef.id,
                    nombre=pdef.nombre,
                    categoria=pdef.categoria,
                    puntaje=None,
                    peso=peso,
                    evidencia=mapa_evidencia.get(pdef.id),
                    fuente=mapa_fuentes.get(pdef.id),
                    estado=estado,
                )
            )
            continue
        if raw is None:
            params.append(
                PuntajeParametro(
                    id=pdef.id,
                    nombre=pdef.nombre,
                    categoria=pdef.categoria,
                    puntaje=None,
                    peso=peso,
                    evidencia=mapa_evidencia.get(pdef.id),
                    fuente=mapa_fuentes.get(pdef.id),
                    estado=estado or "faltante",
                )
            )
            continue
        params.append(
            PuntajeParametro(
                id=pdef.id,
                nombre=pdef.nombre,
                categoria=pdef.categoria,
                puntaje=round(_acotar(raw), 1),
                peso=peso,
                evidencia=mapa_evidencia.get(pdef.id),
                fuente=mapa_fuentes.get(pdef.id),
                estado=estado or "ok",
            )
        )

    by_cat: dict[CategoriaEvaluador, list[PuntajeParametro]] = defaultdict(list)
    for p in params:
        by_cat[p.categoria].append(p)

    categorias: list[PuntajeCategoria] = []
    weighted_total = 0.0
    weight_sum = 0.0
    for cat, plist in by_cat.items():
        measured = [x for x in plist if x.estado == "ok" and x.puntaje is not None]
        if not measured:
            categorias.append(
                PuntajeCategoria(
                    categoria=cat, puntaje=None, puntuado=False, parametros=tuple(plist)
                )
            )
            continue
        w = sum(x.peso for x in measured) or 1.0
        cat_score = sum((x.puntaje or 0.0) * x.peso for x in measured) / w
        categorias.append(
            PuntajeCategoria(
                categoria=cat,
                puntaje=round(cat_score, 1),
                puntuado=True,
                parametros=tuple(plist),
            )
        )
        weighted_total += cat_score * w
        weight_sum += w

    global_pts = round(weighted_total / weight_sum, 1) if weight_sum else None
    meta = {
        **(metadatos or {}),
        "segmento": perfil.segmento,
        "razon_segmento": perfil.razon,
        "parametros_medidos": sum(
            1 for p in params if p.estado == "ok" and p.puntaje is not None
        ),
    }
    return ResultadoEvaluador(
        puntaje_global=global_pts,
        nota=nota_desde_puntaje(global_pts) if global_pts is not None else None,
        categorias=sorted(categorias, key=lambda c: c.categoria),
        parametros=params,
        ficha_fiable=ficha_fiable,
        resumen=resumen,
        recomendaciones=list(recomendaciones or []),
        metadatos=meta,
    )

def bloquear_fisica(
    pistas: dict[str, float],
    evidencia: dict[str, str],
    fuentes: dict[str, str],
    estados: dict[str, str],
    *,
    motivo: str,
) -> None:
    from app.dominio.transparencia.evaluador.parametros import IDS_FISICA

    for pid in IDS_FISICA:
        pistas.pop(pid, None)
        estados[pid] = "sin_puntaje"
        evidencia[pid] = motivo
        fuentes[pid] = "ficha_confidence"
