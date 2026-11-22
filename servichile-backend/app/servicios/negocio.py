from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from datetime import timedelta

from app.dominio.docs_empresa import (
    DOCS_EMPRESA_MAX_BYTES,
    DOCS_EMPRESA_VIGENCIA_DIAS,
    TIPOS_PDF,
    MetaDocEmpresa,
    ResultadoDocEmpresa,
    TipoDocEmpresa,
    es_tipo_doc_empresa,
)
from app.dominio.entidades import (
    DocEmpresaVerificado,
    Metricas,
    Negocio,
    NegocioEnMapa,
    NegocioTitular,
    Reputacion,
)
from app.dominio.errores import (
    DocEmpresaInvalido,
    DocEmpresaMuyGrande,
    NegocioNoEncontrado,
    NoEsTitularDelNegocio,
    EvaluadorIndisponible,
)
from app.dominio.ficha_negocio import normalizar_url_recurso
from app.dominio.oferta_negocio import (
    FiltroListado,
    contrataciones_de,
    industrias_de,
    monto_de,
    plazo_de,
    referencias_de,
    servicios_de,
)
from app.dominio.rut import RutInvalido, normalizar_rut
from app.dominio.telefono import TelefonoInvalido, normalizar_telefono
from app.dominio.puertos import (
    AnalizadorDocEmpresa,
    PuertoEvaluador,
    RepositorioNegocios,
    RepositorioTrabajos,
)
from app.dominio.transparencia.valoracion import calcular_valoracion_documentos
from app.servicios.negocio_reputacion import (
    a_mapa,
    a_titular,
    aplicar_rating_docs,
    docs_copia,
    indice_global,
    metricas_de,
    observables_de,
    persistir_indice,
    reputacion_de,
)
from app.servicios.pades_anti_replay import registrar_hash_unico
from app.tiempo import ahora_utc

log = logging.getLogger(__name__)

__all__ = [
    "ServicioNegocio",
    "NegocioNoEncontrado",
    "NoEsTitularDelNegocio",
    "EvaluadorIndisponible",
]

def rut_desde_documento(texto: str | None) -> str | None:
    if not texto or not str(texto).strip():
        return None
    try:
        return normalizar_rut(str(texto).strip())
    except RutInvalido:
        return None

def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = valor.strip()
    return limpio or None

def _telefono_ficha(valor: str | None) -> str | None:

    texto = _texto_opcional(valor)
    if not texto:
        return None
    try:
        return normalizar_telefono(texto)
    except TelefonoInvalido as error:
        raise DocEmpresaInvalido(str(error)) from None

def normalizar_sitio_web(valor: str | None) -> str | None:

    texto = _texto_opcional(valor)
    if not texto:
        return None
    if not texto.lower().startswith(("http://", "https://")):
        texto = "https://" + texto
    return texto.rstrip("/")

class ServicioNegocio:
    def __init__(
        self,
        negocios: RepositorioNegocios,
        analizador_docs: AnalizadorDocEmpresa | None = None,
        evaluador: PuertoEvaluador | None = None,
        geocodificador=None,
        trabajos: RepositorioTrabajos | None = None,
    ) -> None:
        self.negocios = negocios
        self.analizador_docs = analizador_docs
        self.evaluador = evaluador
        self.geocodificador = geocodificador
        self.trabajos = trabajos

    def _conteos_concretados(
        self, negocio_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if self.trabajos is None or not negocio_ids:
            return {}
        return self.trabajos.contar_concretados_por_negocios(negocio_ids)

    def _proyeccion_titular(self, negocio: Negocio) -> NegocioTitular:
        conteo = self._conteos_concretados([negocio.id]).get(negocio.id, 0)
        return replace(a_titular(negocio), trabajos_concretados=conteo)

    def _aplicar_coordenadas(self, negocio: Negocio, direccion: str | None) -> None:
        if self.geocodificador is None:
            return
        texto = (direccion or "").strip()
        if len(texto) < 3:
            negocio.latitud = None
            negocio.longitud = None
            return
        try:
            coords = self.geocodificador.geocodificar(texto)
        except Exception:
            log.exception("Geocodificación falló para negocio %s", negocio.id)
            return
        if coords is None:
            return
        lat, lng = coords
        negocio.latitud = float(lat)
        negocio.longitud = float(lng)

    def _buscar(self, business_id: uuid.UUID) -> Negocio:
        negocio = self.negocios.obtener(business_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        return negocio

    def listar_para_mapa(self, filtro: FiltroListado | None = None) -> list[NegocioEnMapa]:
        filtro = filtro or FiltroListado()
        filas = self.negocios.listar(filtro)
        conteos = self._conteos_concretados([n.id for n in filas])
        out = [
            replace(a_mapa(n), trabajos_concretados=conteos.get(n.id, 0))
            for n in filas
        ]
        minimo = filtro.concretados_min
        if minimo is not None and minimo > 0:
            out = [m for m in out if m.trabajos_concretados >= minimo]
        return out

    def listar_mios(self, usuario_id: uuid.UUID) -> list[NegocioTitular]:
        filas = self.negocios.listar_de(usuario_id)
        conteos = self._conteos_concretados([n.id for n in filas])
        return [
            replace(a_titular(n), trabajos_concretados=conteos.get(n.id, 0))
            for n in filas
        ]

    def obtener_reputacion(self, business_id: uuid.UUID) -> Reputacion:

        from app.servicios.negocio_reputacion import metricas_de

        negocio = self._buscar(business_id)
        metricas = metricas_de(negocio)
        nota_publicada = float(metricas.final_score or 0.0)
        conteo = self._conteos_concretados([negocio.id]).get(negocio.id, 0)
        persistir_indice(negocio, trabajos_concretados=conteo)

        metricas.final_score = nota_publicada
        return reputacion_de(negocio)

    def respuesta_doc_empresa(
        self, negocio: Negocio, tipo: str, resultado: ResultadoDocEmpresa
    ) -> DocEmpresaVerificado:

        docs = docs_copia(negocio)
        rating = calcular_valoracion_documentos(docs)
        indice, pct = indice_global(metricas_de(negocio))
        return DocEmpresaVerificado(
            business_id=negocio.id,
            tipo=tipo,
            verificado=True,
            score=resultado.score,
            senales=tuple(resultado.senales),
            docs_empresa=docs,
            indice_transparencia=indice,
            indice_pct=pct,
            docs_verificados=rating.verificados,
            docs_total=rating.total,
            verificado_criptograficamente=bool(
                resultado.verificado_criptograficamente
            ),
            entidad_emisora=resultado.entidad_emisora,
            fecha_emision=resultado.fecha_emision,
            sha256_hash=resultado.sha256_hash,
            glosa=resultado.glosa,
            motivo=resultado.motivo
            or "Documento de empresa validado.",
        )

    def respuesta_doc_revocado(
        self, negocio: Negocio, tipo: str
    ) -> DocEmpresaVerificado:
        docs = docs_copia(negocio)
        rating = calcular_valoracion_documentos(docs)
        indice, pct = indice_global(metricas_de(negocio))
        return DocEmpresaVerificado(
            business_id=negocio.id,
            tipo=tipo,
            verificado=False,
            score=0,
            senales=(),
            docs_empresa=docs,
            indice_transparencia=indice,
            indice_pct=pct,
            docs_verificados=rating.verificados,
            docs_total=rating.total,
            verificado_criptograficamente=False,
            entidad_emisora=None,
            fecha_emision=None,
            sha256_hash=None,
            glosa=None,
            motivo="Documento revocado. Suba un PDF nuevo para revalidar.",
        )

    def _aplicar_evaluador(
        self, negocio: Negocio, *, exigir_evaluador: bool = False
    ) -> Negocio:

        if self.evaluador is None:
            if exigir_evaluador:
                raise EvaluadorIndisponible("Evaluador de señales no disponible.")
            persistir_indice(negocio)
            return self.negocios.guardar(negocio)
        try:
            resultado = self.evaluador.evaluar(negocio)
        except Exception:
            log.exception("Evaluador de señales falló para negocio %s", negocio.id)
            if exigir_evaluador:
                raise EvaluadorIndisponible(
                    "Falló la evaluación de señales externas."
                ) from None
            persistir_indice(negocio)
            return self.negocios.guardar(negocio)
        observables = resultado.a_observables()
        metricas = metricas_de(negocio)
        meta = resultado.metadatos or {}
        places_rl = meta.get("places", {}).get("modo") == "limite_cuota"
        places_sin_fisica = not any(
            o.id.startswith("fis_") for o in observables
        )
        rastreador_fail = meta.get("rastreador_web", {}).get("modo") == "fallido"
        if places_rl or places_sin_fisica:

            observables = self._conservar_fisica_previa(metricas, observables)
        if rastreador_fail:

            observables = self._conservar_sitio_previa(metricas, observables)
        global_pts = resultado.puntaje_global
        pct_eval = float(global_pts) if global_pts is not None else 0.0
        if places_rl or places_sin_fisica or rastreador_fail:
            from app.servicios.negocio_reputacion import pct_evaluador_desde_observables

            recal = pct_evaluador_desde_observables(observables)
            if recal is not None:
                pct_eval = float(recal)
        conteo_trab = self._conteos_concretados([negocio.id]).get(negocio.id, 0)
        persistir_indice(
            negocio,
            senales=observables,
            pct_evaluador=pct_eval,
            trabajos_concretados=conteo_trab,
        )
        metricas.rater_escaneado_en = ahora_utc()
        for obs in observables:
            if obs.id == "fis_rating" and obs.score > 0:
                metricas.google_rating_avg = round((obs.score / 100.0) * 5.0, 1)
            if obs.id == "fis_reviews" and obs.score > 0:
                metricas.google_reviews_count = max(
                    metricas.google_reviews_count or 0, int((obs.score - 20) / 2)
                )
        return self.negocios.guardar(negocio)

    @staticmethod
    def _conservar_fisica_previa(metricas, observables: list):

        from app.dominio.entidades import ObservableSenal

        prev = {
            o.id: o
            for o in observables_de(metricas)
            if o.id.startswith("fis_") or o.id == "dig_website"
        }
        by_id = {o.id: o for o in observables}

        avg = metricas.google_rating_avg
        count = metricas.google_reviews_count or 0
        if avg and (not prev.get("fis_rating") or prev["fis_rating"].score <= 0):
            prev["fis_places_exists"] = ObservableSenal(
                id="fis_places_exists",
                etiqueta="Aparece en Google como negocio",
                detalle="",
                score=100,
                peso="1.0",
                grupo="operativa",
            )
            prev["fis_rating"] = ObservableSenal(
                id="fis_rating",
                etiqueta="Nota de clientes en Google",
                detalle=f"{avg}/5",
                score=int(round(min(100.0, (float(avg) / 5.0) * 100.0))),
                peso="1.0",
                grupo="operativa",
            )
            if count:
                prev["fis_reviews"] = ObservableSenal(
                    id="fis_reviews",
                    etiqueta="Cantidad de reseñas de clientes",
                    detalle=f"{count} reseñas",
                    score=int(round(min(100.0, 20.0 + float(count) * 2.0))),
                    peso="1.0",
                    grupo="operativa",
                )
        if not prev:
            return observables
        out = []
        for o in observables:

            if o.id in prev and prev[o.id].score > 0 and o.score <= 0:
                out.append(prev[o.id])
            else:
                out.append(o)
        for oid, po in prev.items():
            if oid not in by_id and po.score > 0:
                out.append(po)
        return out

    @staticmethod
    def _conservar_sitio_previa(metricas, observables: list):

        from app.dominio.transparencia.evaluador.parametros import IDS_SITIO

        ids = set(IDS_SITIO)
        prev = {
            o.id: o for o in observables_de(metricas) if o.id in ids and o.score > 0
        }
        if not prev:
            return observables
        by_id = {o.id: o for o in observables}
        out = []
        for o in observables:
            if o.id in prev and o.score <= 0:
                out.append(prev[o.id])
            else:
                out.append(o)
        for oid, po in prev.items():
            if oid not in by_id:
                out.append(po)
        return out

    def refrescar_evaluador(self, business_id: uuid.UUID) -> Negocio:
        return self._aplicar_evaluador(self._buscar(business_id))

    def refrescar_indice_titular(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> Reputacion:

        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        actualizado = self._aplicar_evaluador(negocio, exigir_evaluador=True)
        return reputacion_de(actualizado)

    def refrescar_evaluador_todos(self, limite: int = 500) -> int:
        n = 0
        for negocio in self.negocios.listar_completos(limite=limite):
            try:
                self._aplicar_evaluador(negocio)
                n += 1
            except Exception:
                log.exception(
                    "Evaluador en segundo plano: fallo en negocio %s", negocio.id
                )
                continue
        return n

    def crear(
        self,
        usuario_id: uuid.UUID,
        *,
        nombre: str,
        categoria: str,
        direccion: str | None = None,
        descripcion: str | None = None,
        telefono: str | None = None,
        sitio_web: str | None = None,
        imagen_url: str | None = None,
        logo_url: str | None = None,
        rut_empresa: str | None = None,
        servicios: list[str] | None = None,
        industrias: list[str] | None = None,
        contrataciones: list[str] | None = None,
        monto: str | None = None,
        plazo: str | None = None,
        referencias: list[str] | None = None,
        commit: bool = True,
    ) -> NegocioTitular:
        negocio_id = uuid.uuid4()
        negocio = Negocio(
            id=negocio_id,
            nombre=nombre.strip(),
            categoria=categoria,
            direccion=_texto_opcional(direccion),
            descripcion=_texto_opcional(descripcion),
            telefono=_telefono_ficha(telefono),
            sitio_web=normalizar_sitio_web(sitio_web),
            imagen_url=normalizar_url_recurso(imagen_url),
            logo_url=normalizar_url_recurso(logo_url),
            servicios=servicios_de(servicios),
            industrias=industrias_de(industrias),
            contrataciones=contrataciones_de(contrataciones),
            monto=monto_de(monto),
            plazo=plazo_de(plazo),
            referencias=referencias_de(referencias),
            is_claimed=True,
            reclamado_por=usuario_id,
            rut_empresa=rut_desde_documento(rut_empresa),
            docs_empresa={},
            metricas=Metricas(
                business_id=negocio_id,
                google_reviews_count=0,
                final_score=0.0,
                actualizado_en=ahora_utc(),
            ),
        )
        self._aplicar_coordenadas(negocio, negocio.direccion)

        guardado = self.negocios.guardar(negocio, commit=commit)
        return self._proyeccion_titular(guardado)

    def eliminar(self, business_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        self.negocios.eliminar(business_id)

    def actualizar_rut_empresa(
        self, business_id: uuid.UUID, usuario_id: uuid.UUID, rut: str
    ) -> tuple[NegocioTitular, bool]:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        normalizado = rut_desde_documento(rut)
        if not normalizado:
            raise DocEmpresaInvalido("RUT de empresa inválido.")
        negocio.rut_empresa = normalizado
        metricas = metricas_de(negocio)
        metricas.rater_escaneado_en = None
        guardado = self.negocios.guardar(negocio)
        return self._proyeccion_titular(guardado), True

    @staticmethod
    def _firma_evaluador(negocio: Negocio) -> tuple[str, ...]:

        return (
            (negocio.nombre or "").strip().casefold(),
            (negocio.categoria or "").strip().casefold(),
            (negocio.direccion or "").strip().casefold(),
            (negocio.telefono or "").strip(),
            (negocio.sitio_web or "").strip().casefold(),
            (negocio.rut_empresa or "").strip().upper(),
        )

    def actualizar(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        *,
        nombre: str,
        categoria: str,
        direccion: str | None = None,
        descripcion: str | None = None,
        telefono: str | None = None,
        sitio_web: str | None = None,
        imagen_url: str | None = None,
        logo_url: str | None = None,
        rut_empresa: str | None = None,
        servicios: list[str] | None = None,
        industrias: list[str] | None = None,
        contrataciones: list[str] | None = None,
        monto: str | None = None,
        plazo: str | None = None,
        referencias: list[str] | None = None,
    ) -> tuple[NegocioTitular, bool]:
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        firma_antes = self._firma_evaluador(negocio)
        negocio.nombre = nombre.strip()
        negocio.categoria = categoria
        negocio.direccion = _texto_opcional(direccion)
        negocio.descripcion = _texto_opcional(descripcion)
        negocio.telefono = _telefono_ficha(telefono)
        negocio.sitio_web = normalizar_sitio_web(sitio_web)
        negocio.imagen_url = normalizar_url_recurso(imagen_url)
        negocio.logo_url = normalizar_url_recurso(logo_url)
        negocio.servicios = servicios_de(servicios)
        negocio.industrias = industrias_de(industrias)
        negocio.contrataciones = contrataciones_de(contrataciones)
        negocio.monto = monto_de(monto)
        negocio.plazo = plazo_de(plazo)
        negocio.referencias = referencias_de(referencias)
        if rut_empresa is not None and str(rut_empresa).strip():
            normalizado = rut_desde_documento(rut_empresa)
            if not normalizado:
                raise DocEmpresaInvalido("RUT de empresa inválido.")
            negocio.rut_empresa = normalizado
        self._aplicar_coordenadas(negocio, negocio.direccion)
        guardado = self.negocios.guardar(negocio)
        if self._firma_evaluador(guardado) != firma_antes:
            metricas = metricas_de(guardado)
            metricas.rater_escaneado_en = None
            guardado = self.negocios.guardar(guardado)
            return self._proyeccion_titular(guardado), True
        persistir_indice(guardado)
        guardado = self.negocios.guardar(guardado)
        return self._proyeccion_titular(guardado), False

    def eliminar_todos_del_usuario(self, usuario_id: uuid.UUID) -> None:
        self.negocios.eliminar_de(usuario_id)

    def _aplicar_resultado_doc(
        self,
        negocio: Negocio,
        tipo_doc: TipoDocEmpresa,
        resultado: ResultadoDocEmpresa,
        *,
        usuario_id: uuid.UUID,
    ) -> Negocio:
        registrar_hash_unico(
            self.negocios,
            resultado.sha256_hash,
            scope="empresa",
            tipo=tipo_doc,
            usuario_id=usuario_id,
            business_id=negocio.id,
            al_rechazar=lambda: DocEmpresaInvalido(
                "Este documento (hash) ya fue utilizado. No se admite reutilizar el mismo PDF."
            ),
        )
        docs = docs_copia(negocio)
        ahora = ahora_utc()
        meta = MetaDocEmpresa(
            verificado=True,
            score=resultado.score,
            senales=list(resultado.senales),
            verificado_en=ahora.isoformat(),
            vence_en=(ahora + timedelta(days=DOCS_EMPRESA_VIGENCIA_DIAS)).isoformat(),
            rut_detectado=resultado.rut_detectado,
            grupo=resultado.grupo,
        )
        if resultado.verificado_criptograficamente:
            meta.verificado_criptograficamente = True
            meta.entidad_emisora = resultado.entidad_emisora
            meta.fecha_emision = resultado.fecha_emision
            meta.sha256_hash = resultado.sha256_hash
            meta.glosa = resultado.glosa
            meta.documento_tipo = tipo_doc.upper()
        docs[tipo_doc] = meta
        negocio.docs_empresa = docs
        aplicar_rating_docs(negocio)
        return self.negocios.guardar(negocio)

    def revocar_doc_empresa(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tipo: str,
    ) -> Negocio:
        if not es_tipo_doc_empresa(tipo) or tipo not in TIPOS_PDF:
            raise DocEmpresaInvalido(
                "Tipo PDF inválido. Use los documentos Grupo 1/2 (PDF textual)."
            )
        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()
        docs = docs_copia(negocio)
        if tipo not in docs:
            raise DocEmpresaInvalido(
                "No hay un documento verificado de ese tipo para revocar."
            )
        del docs[tipo]
        negocio.docs_empresa = docs
        aplicar_rating_docs(negocio)
        return self.negocios.guardar(negocio)

    def procesar_doc_empresa(
        self,
        business_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tipo: str,
        contenido: bytes,
        nombre_archivo: str | None = None,
    ) -> tuple[Negocio, ResultadoDocEmpresa]:
        if not es_tipo_doc_empresa(tipo) or tipo not in TIPOS_PDF:
            raise DocEmpresaInvalido(
                "Tipo PDF inválido. Use los documentos Grupo 1/2 (PDF textual)."
            )
        if self.analizador_docs is None:
            raise DocEmpresaInvalido(
                "Analizador de documentos de empresa no disponible."
            )
        if len(contenido) > DOCS_EMPRESA_MAX_BYTES:
            raise DocEmpresaMuyGrande("El PDF supera el tamaño máximo de 8 MB.")
        if not contenido.startswith(b"%PDF"):
            raise DocEmpresaInvalido(
                "Solo se acepta PDF con texto real. No se admiten fotos ni imágenes."
            )

        negocio = self._buscar(business_id)
        if negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()

        tipo_doc: TipoDocEmpresa = tipo
        resultado = self.analizador_docs.analizar(
            contenido,
            tipo=tipo_doc,
            rut_empresa=negocio.rut_empresa,
            nombre_empresa=negocio.nombre,
            nombre_archivo=nombre_archivo,
        )
        if not resultado.aceptado:
            raise DocEmpresaInvalido(resultado.motivo)

        return (
            self._aplicar_resultado_doc(
                negocio, tipo_doc, resultado, usuario_id=usuario_id
            ),
            resultado,
        )
