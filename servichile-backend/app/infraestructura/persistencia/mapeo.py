

from __future__ import annotations

from sqlalchemy.orm import joinedload, load_only

from app.dominio.docs_empresa import docs_empresa_desde_raw
from app.dominio.entidades import Metricas, Negocio, Perfil, Trabajo, Usuario
from app.infraestructura.persistencia import modelos as orm

def _perfil(p: orm.Perfil | None) -> Perfil | None:

    if p is None:

        return None

    return Perfil(
        edad=p.edad,
        tipo_cuenta=p.tipo_cuenta,
    )

def _usuario(u: orm.Usuario) -> Usuario:

    return Usuario(
        id=u.id,
        email=u.email,
        nombre=u.nombre,
        password_hash=u.password_hash,
        activo=u.activo,
        rut=u.rut,
        rut_verificado=u.rut_verificado,
        telefono=u.telefono,
        biometria_verificada=bool(u.biometria_verificada),
        biometria_verificada_en=u.biometria_verificada_en,
        biometria_ruta=u.biometria_ruta,
        biometria_sha256=u.biometria_sha256,
        biometria_bytes=u.biometria_bytes,
        biometria_ancho=u.biometria_ancho,
        biometria_alto=u.biometria_alto,
        biometria_content_type=u.biometria_content_type,
        biometria_retener_hasta=u.biometria_retener_hasta,
        cedula_verificada=bool(u.cedula_verificada),
        cedula_verificada_en=u.cedula_verificada_en,
        cedula_ruta=u.cedula_ruta,
        cedula_sha256=u.cedula_sha256,
        cedula_bytes=u.cedula_bytes,
        cedula_ancho=u.cedula_ancho,
        cedula_alto=u.cedula_alto,
        cedula_content_type=u.cedula_content_type,
        cedula_retener_hasta=u.cedula_retener_hasta,
        cedula_score=u.cedula_score,
        cedula_rut_ocr=u.cedula_rut_ocr,
        antecedentes_verificados=bool(u.antecedentes_verificados),
        antecedentes_verificados_en=u.antecedentes_verificados_en,
        antecedentes_anotaciones=u.antecedentes_anotaciones,
        antecedentes_score=u.antecedentes_score,
        antecedentes_pades=bool(u.antecedentes_pades),
        antecedentes_entidad_emisora=u.antecedentes_entidad_emisora,
        antecedentes_fecha_emision=u.antecedentes_fecha_emision,
        antecedentes_sha256=u.antecedentes_sha256,
        antecedentes_glosa=u.antecedentes_glosa,
        aval_verificado=bool(u.aval_verificado),
        aval_verificado_en=u.aval_verificado_en,
        aval_score=u.aval_score,
        aval_tipo=u.aval_tipo,
        xp=int(u.xp or 0),
        creado_en=u.creado_en,
        perfil=_perfil(u.perfil),
    )

def _metricas(m: orm.MetricasReputacionNegocio | None) -> Metricas | None:

    if m is None:

        return None

    return Metricas(
        business_id=m.business_id,
        google_rating_avg=m.google_rating_avg,
        google_reviews_count=m.google_reviews_count or 0,
        final_score=m.final_score,
        rater_escaneado_en=m.rater_escaneado_en,
        observables=(
            list(m.observables)
            if isinstance(m.observables, list)
            else None
        ),
        actualizado_en=m.actualizado_en,
    )

def _textos(valor) -> tuple[str, ...]:
    if not isinstance(valor, (list, tuple)):
        return ()
    return tuple(str(item) for item in valor if isinstance(item, str) and item.strip())

def _oferta(n: orm.EntidadNegocio) -> dict:
    return {
        "servicios": _textos(n.servicios),
        "industrias": _textos(n.industrias),
        "contrataciones": _textos(n.contrataciones),
        "monto": n.monto,
        "plazo": n.plazo,
        "referencias": _textos(n.referencias),
    }

def _negocio_lista(n: orm.EntidadNegocio) -> Negocio:

    m = n.metricas

    metricas = None

    if m is not None:

        metricas = Metricas(
            business_id=m.business_id,
            google_rating_avg=m.google_rating_avg,
            google_reviews_count=m.google_reviews_count or 0,
            final_score=m.final_score,
            actualizado_en=m.actualizado_en,
        )

    return Negocio(
        id=n.id,
        nombre=n.nombre,
        categoria=n.categoria,
        latitud=n.latitud,
        longitud=n.longitud,
        direccion=n.direccion,
        descripcion=n.descripcion,
        imagen_url=n.imagen_url,
        logo_url=n.logo_url,
        requiere_nivel=n.requiere_nivel,
        is_claimed=n.is_claimed,
        rut_empresa=n.rut_empresa,
        docs_empresa=docs_empresa_desde_raw(n.docs_empresa),
        metricas=metricas,
        **_oferta(n),
    )

def _opciones_lista():

    return (
        load_only(
            orm.EntidadNegocio.id,
            orm.EntidadNegocio.nombre,
            orm.EntidadNegocio.categoria,
            orm.EntidadNegocio.latitud,
            orm.EntidadNegocio.longitud,
            orm.EntidadNegocio.direccion,
            orm.EntidadNegocio.descripcion,
            orm.EntidadNegocio.servicios,
            orm.EntidadNegocio.industrias,
            orm.EntidadNegocio.contrataciones,
            orm.EntidadNegocio.monto,
            orm.EntidadNegocio.plazo,
            orm.EntidadNegocio.referencias,
            orm.EntidadNegocio.imagen_url,
            orm.EntidadNegocio.logo_url,
            orm.EntidadNegocio.requiere_nivel,
            orm.EntidadNegocio.is_claimed,
            orm.EntidadNegocio.rut_empresa,
            orm.EntidadNegocio.docs_empresa,
        ),
        joinedload(orm.EntidadNegocio.metricas).load_only(
            orm.MetricasReputacionNegocio.business_id,
            orm.MetricasReputacionNegocio.google_rating_avg,
            orm.MetricasReputacionNegocio.google_reviews_count,
            orm.MetricasReputacionNegocio.final_score,
            orm.MetricasReputacionNegocio.actualizado_en,
        ),
    )

def _negocio(n: orm.EntidadNegocio) -> Negocio:

    return Negocio(
        id=n.id,
        nombre=n.nombre,
        categoria=n.categoria,
        latitud=n.latitud,
        longitud=n.longitud,
        direccion=n.direccion,
        descripcion=n.descripcion,
        imagen_url=n.imagen_url,
        logo_url=n.logo_url,
        requiere_nivel=n.requiere_nivel,
        is_claimed=n.is_claimed,
        reclamado_por=n.reclamado_por,
        telefono=n.telefono,
        sitio_web=n.sitio_web,
        rut_empresa=n.rut_empresa,
        docs_empresa=docs_empresa_desde_raw(n.docs_empresa),
        metricas=_metricas(n.metricas),
        **_oferta(n),
    )

def _trabajo(r: orm.Trabajo) -> Trabajo:

    return Trabajo(
        id=r.id,
        usuario_id=r.usuario_id,
        business_id=r.business_id,
        estado=r.estado,
        qr_token=r.qr_token,
        creado_en=r.creado_en,
        actualizado_en=r.actualizado_en,
    )

