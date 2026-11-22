

from __future__ import annotations

from dataclasses import dataclass

from app.dominio.docs_empresa import (
    DocsEmpresa,
    MetaDocEmpresa,
    TIPOS_DOC_EMPRESA,
    label_tipo,
    meta_doc_esta_vigente,
)
from app.dominio.entidades import ObservableSenal

_TOTAL_DOCS = len(TIPOS_DOC_EMPRESA)

_PESO_EVALUADOR = 0.5
_PESO_DOCS = 0.5

@dataclass(frozen=True, slots=True)
class ValoracionDocumentos:
    verificados: int
    total: int
    pct: int
    indice: float

_VALORACION_VACIA = ValoracionDocumentos(0, _TOTAL_DOCS, 0, 0.0)
_VALORACION_COMPLETA = ValoracionDocumentos(_TOTAL_DOCS, _TOTAL_DOCS, 100, 10.0)

def _meta_verificado(meta: object) -> bool:
    return isinstance(meta, MetaDocEmpresa) and meta_doc_esta_vigente(meta)

def doc_esta_verificado(docs: DocsEmpresa | None, tipo: str) -> bool:
    if not docs:
        return False
    return _meta_verificado(docs.get(tipo))

def calcular_valoracion_documentos(docs: DocsEmpresa | None) -> ValoracionDocumentos:

    if not docs:
        return _VALORACION_VACIA

    verificados = 0
    for tipo in TIPOS_DOC_EMPRESA:
        if _meta_verificado(docs.get(tipo)):
            verificados += 1

    if verificados == 0:
        return _VALORACION_VACIA
    if verificados >= _TOTAL_DOCS:
        return _VALORACION_COMPLETA

    return ValoracionDocumentos(
        verificados=verificados,
        total=_TOTAL_DOCS,
        pct=int(round(100.0 * verificados / _TOTAL_DOCS)),
        indice=round(10.0 * verificados / _TOTAL_DOCS, 1),
    )

def score_unificado(*, pct_evaluador: float | None, docs_pct: int) -> tuple[float, int]:

    r = 0.0 if pct_evaluador is None else max(0.0, min(100.0, float(pct_evaluador)))
    d = max(0, min(100, int(docs_pct)))
    pct = int(round(_PESO_EVALUADOR * r + _PESO_DOCS * d))
    return round(pct / 10.0, 1), pct

def observables_documentos(docs: DocsEmpresa | None) -> list[ObservableSenal]:

    out: list[ObservableSenal] = []
    for tipo in TIPOS_DOC_EMPRESA:
        ok = doc_esta_verificado(docs, tipo)
        out.append(
            ObservableSenal(
                id=f"doc_{tipo}",
                etiqueta=label_tipo(tipo),
                detalle="",
                score=100 if ok else 0,
                peso="1.0",
                grupo="documentos",
                razones=[],
            )
        )
    return out

def calcular_indice(docs: DocsEmpresa | None = None) -> float:
    return calcular_valoracion_documentos(docs).indice

def es_observable_documento(oid: str) -> bool:
    return str(oid or "").startswith("doc_")

IDS_OBSERVABLES_TEASER: tuple[str, ...] = (
    "doc_patente",
    "fis_reviews",
    "cyb_referrer",
)

_TEASER_META: dict[str, tuple[str, str]] = {
    "doc_patente": ("Patente municipal vigente", "documentos"),
    "fis_reviews": ("Cantidad de reseñas de clientes", "operativa"),
    "cyb_referrer": ("Referrer-Policy", "ciber"),
}

def catalogo_observables_esperado() -> int:

    from app.dominio.docs_empresa import TIPOS_DOC_EMPRESA
    from app.dominio.transparencia.evaluador.parametros import PARAMETROS

    return len(PARAMETROS) + len(TIPOS_DOC_EMPRESA) + 1

def teaser_observables_publico(
    observables: list[ObservableSenal] | None,
) -> tuple[list[ObservableSenal], int]:

    lista = list(observables or [])
    by_id = {o.id: o for o in lista}
    total = len(lista) if lista else catalogo_observables_esperado()
    if total < len(IDS_OBSERVABLES_TEASER):
        total = catalogo_observables_esperado()
    out: list[ObservableSenal] = []
    for oid in IDS_OBSERVABLES_TEASER:
        if oid in by_id:
            out.append(by_id[oid])
            continue
        etiqueta, grupo = _TEASER_META[oid]
        out.append(
            ObservableSenal(
                id=oid,
                etiqueta=etiqueta,
                detalle="",
                score=0,
                peso="1.0",
                grupo=grupo,
                razones=[],
            )
        )
    restantes = max(0, total - len(out))
    return out, restantes
