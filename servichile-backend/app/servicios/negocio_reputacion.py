

from __future__ import annotations

from app.dominio.docs_empresa import DocsEmpresa, MetaDocEmpresa, meta_doc_esta_vigente
from app.dominio.entidades import (
    Metricas,
    Negocio,
    NegocioEnMapa,
    NegocioTitular,
    ObservableSenal,
    Reputacion,
)
from app.dominio.ficha_negocio import (
    cta_texto,
    imagen_efectiva,
    logo_efectivo,
    logo_texto,
)
from app.dominio.transparencia.trabajos_indice import (
    ID_TRABAJOS_CONCRETADOS,
    es_observable_trabajos,
    observable_trabajos_concretados,
)
from app.dominio.transparencia.valoracion import (
    ValoracionDocumentos,
    calcular_valoracion_documentos,
    es_observable_documento,
    observables_documentos,
    score_unificado,
)
from app.tiempo import ahora_utc

def metricas_de(negocio: Negocio) -> Metricas:
    if negocio.metricas is None:
        negocio.metricas = Metricas(
            business_id=negocio.id,
            google_reviews_count=0,
            final_score=0.0,
            actualizado_en=ahora_utc(),
        )
    return negocio.metricas

def pct_evaluador_desde_observables(obs: list[ObservableSenal]) -> float | None:
    senales = [o for o in obs if not es_observable_documento(o.id)]
    if not senales:
        return None
    acc = 0.0
    peso = 0.0
    for o in senales:
        try:
            w = float(o.peso)
        except (TypeError, ValueError):
            w = 1.0
        w = max(0.05, w)
        acc += o.score * w
        peso += w
    return acc / peso if peso else 0.0

def indice_global(metricas: Metricas) -> tuple[float, int]:

    v = round(float(metricas.final_score or 0.0), 1)
    return v, int(max(0, min(100, round(v * 10))))

def obs_a_dict(obs: ObservableSenal) -> dict:
    return {
        "id": obs.id,
        "etiqueta": obs.etiqueta,
        "detalle": obs.detalle or "",
        "score": int(obs.score),
        "peso": obs.peso,
        "grupo": obs.grupo,
        "razones": list(obs.razones or []),
    }

def observables_de(metricas: Metricas) -> list[ObservableSenal]:
    raw = metricas.observables
    if not isinstance(raw, list):
        return []
    out: list[ObservableSenal] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        oid = str(item.get("id") or "").strip()
        if not oid:
            continue
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        grupo = str(item.get("grupo") or "operativa")
        if grupo not in (
            "ciber",
            "operativa",
            "contractual",
            "legal",
            "documentos",
            "plataforma",
        ):
            grupo = "operativa"
        razones = item.get("razones") if isinstance(item.get("razones"), list) else []
        out.append(
            ObservableSenal(
                id=oid,
                etiqueta=str(item.get("etiqueta") or oid),
                detalle=str(item.get("detalle") or ""),
                score=score,
                peso=str(item.get("peso") or "1.0"),
                grupo=grupo,
                razones=[str(x) for x in razones],
            )
        )
    return out

def persistir_indice(
    negocio: Negocio,
    *,
    senales: list[ObservableSenal] | None = None,
    pct_evaluador: float | None = None,
    trabajos_concretados: int | None = None,
) -> ValoracionDocumentos:

    metricas = metricas_de(negocio)
    docs = negocio.docs_empresa or {}
    docs_rating = calcular_valoracion_documentos(docs)
    base = (
        list(senales)
        if senales is not None
        else [
            o
            for o in observables_de(metricas)
            if not es_observable_documento(o.id)
        ]
    )

    if senales is not None:
        vistos = {o.id for o in base}
        for prev in observables_de(metricas):
            if (
                es_observable_documento(prev.id)
                or es_observable_trabajos(prev.id)
                or prev.id in vistos
            ):
                continue
            if prev.score > 0:
                base.append(prev)
                vistos.add(prev.id)
    prev_trabajos = next(
        (o for o in base if o.id == ID_TRABAJOS_CONCRETADOS), None
    )
    if prev_trabajos is None:
        prev_trabajos = next(
            (
                o
                for o in observables_de(metricas)
                if o.id == ID_TRABAJOS_CONCRETADOS
            ),
            None,
        )
    base = [o for o in base if o.id != ID_TRABAJOS_CONCRETADOS]
    if trabajos_concretados is not None:
        base.append(observable_trabajos_concretados(trabajos_concretados))
    elif prev_trabajos is not None:
        base.append(prev_trabajos)
    if pct_evaluador is None:
        pct_evaluador = pct_evaluador_desde_observables(base)
    indice, _pct = score_unificado(pct_evaluador=pct_evaluador, docs_pct=docs_rating.pct)
    metricas.final_score = indice
    metricas.observables = [
        obs_a_dict(o) for o in observables_documentos(docs) + base
    ]
    metricas.actualizado_en = ahora_utc()
    return docs_rating

def aplicar_rating_docs(negocio: Negocio) -> ValoracionDocumentos:
    return persistir_indice(negocio)

def docs_copia(negocio: Negocio) -> DocsEmpresa:
    return dict(negocio.docs_empresa or {})

def docs_publicos(negocio: Negocio) -> DocsEmpresa:

    out: DocsEmpresa = {}
    for tipo, meta in (negocio.docs_empresa or {}).items():
        if not isinstance(meta, MetaDocEmpresa):
            continue
        vigente = meta_doc_esta_vigente(meta)
        flag = MetaDocEmpresa(verificado=vigente)
        if meta.verificado_en:
            flag.verificado_en = meta.verificado_en
        if meta.vence_en:
            flag.vence_en = meta.vence_en
        out[str(tipo)] = flag
    return out

def a_mapa(negocio: Negocio) -> NegocioEnMapa:

    metricas = metricas_de(negocio)
    indice, pct = indice_global(metricas)
    return NegocioEnMapa(
        id=negocio.id,
        nombre=negocio.nombre,
        categoria=negocio.categoria,
        latitud=negocio.latitud,
        longitud=negocio.longitud,
        direccion=negocio.direccion,
        descripcion=negocio.descripcion,
        imagen_url=imagen_efectiva(negocio.imagen_url, negocio.categoria),
        logo_url=logo_efectivo(negocio.logo_url),
        logo_texto=logo_texto(negocio.nombre),
        cta_texto=cta_texto(negocio.categoria),
        indice_transparencia=indice,
        indice_pct=pct,
        requiere_nivel=negocio.requiere_nivel,
        is_claimed=bool(negocio.is_claimed),
        servicios=tuple(negocio.servicios or ()),
        industrias=tuple(negocio.industrias or ()),
        contrataciones=tuple(negocio.contrataciones or ()),
        monto=negocio.monto,
        plazo=negocio.plazo,
        referencias=tuple(negocio.referencias or ()),
    )

def a_titular(negocio: Negocio) -> NegocioTitular:

    metricas = metricas_de(negocio)
    indice, pct = indice_global(metricas)
    return NegocioTitular(
        id=negocio.id,
        nombre=negocio.nombre,
        categoria=negocio.categoria,
        latitud=negocio.latitud,
        longitud=negocio.longitud,
        direccion=negocio.direccion,
        descripcion=negocio.descripcion,
        imagen_url=imagen_efectiva(negocio.imagen_url, negocio.categoria),
        logo_url=logo_efectivo(negocio.logo_url),
        logo_texto=logo_texto(negocio.nombre),
        cta_texto=cta_texto(negocio.categoria),
        indice_transparencia=indice,
        indice_pct=pct,
        requiere_nivel=negocio.requiere_nivel,
        is_claimed=bool(negocio.is_claimed),
        docs_empresa=docs_copia(negocio),
        rut_empresa=negocio.rut_empresa,
        telefono=negocio.telefono,
        sitio_web=negocio.sitio_web,
        rater_listo=bool(metricas.rater_escaneado_en),
        servicios=tuple(negocio.servicios or ()),
        industrias=tuple(negocio.industrias or ()),
        contrataciones=tuple(negocio.contrataciones or ()),
        monto=negocio.monto,
        plazo=negocio.plazo,
        referencias=tuple(negocio.referencias or ()),
    )

_DESCARGO = (
    "Índice global a partir de señales públicas (ficha, sitio, "
    "compras públicas, etc.). No constituye un juicio sobre la calidad del servicio."
)

def reputacion_de(negocio: Negocio) -> Reputacion:

    docs_rating = calcular_valoracion_documentos(negocio.docs_empresa)
    metricas = metricas_de(negocio)
    indice, pct = indice_global(metricas)
    observables = observables_de(metricas)
    google_avg = metricas.google_rating_avg
    google_count = metricas.google_reviews_count or 0
    for obs in observables:
        if obs.id == "fis_rating" and obs.score > 0 and google_avg is None:
            google_avg = round((obs.score / 100.0) * 5.0, 1)
        if obs.id == "fis_reviews" and obs.score > 0 and not google_count:
            google_count = max(0, int((obs.score - 20) / 2))
    return Reputacion(
        business_id=negocio.id,
        nombre=negocio.nombre,
        categoria=negocio.categoria,
        google_rating_avg=google_avg,
        google_reviews_count=google_count,
        indice_transparencia=indice,
        indice_pct=pct,
        docs_verificados=docs_rating.verificados,
        docs_total=docs_rating.total,
        docs_empresa=docs_publicos(negocio),
        actualizado_en=metricas.rater_escaneado_en or metricas.actualizado_en,
        observables=observables,
        rater_listo=bool(metricas.rater_escaneado_en),
        descargo=_DESCARGO,
    )
