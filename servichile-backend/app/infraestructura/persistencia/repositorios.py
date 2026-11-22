import uuid

from sqlalchemy import String, cast, func, select
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session, joinedload

from app.dominio.docs_empresa import docs_empresa_a_raw
from app.dominio.entidades import Negocio, Trabajo, Usuario
from app.dominio.errores import RutEmpresaEnUso
from app.dominio.oferta_negocio import FiltroListado
from app.dominio.pago_informe import CompraInforme
from app.dominio.pago_publicacion import CompraPublicacion
from app.infraestructura.persistencia import modelos as orm
from app.infraestructura.persistencia.mapeo import (
    _negocio,
    _negocio_lista,
    _opciones_lista,
    _trabajo,
    _usuario,
)
from app.tiempo import ahora_utc

def _compra_informe(r: orm.CompraInforme) -> CompraInforme:
    return CompraInforme(
        id=r.id,
        usuario_id=r.usuario_id,
        business_id=r.business_id,
        buy_order=r.buy_order,
        monto=int(r.monto),
        estado=r.estado,
        token=r.token,
        response_code=r.response_code,
        authorization_code=r.authorization_code,
        payment_type_code=r.payment_type_code,
        card_last4=r.card_last4,
        error_codigo=r.error_codigo,
        error_detalle=r.error_detalle,
        creado_en=r.creado_en,
        actualizado_en=r.actualizado_en,
    )

class RepositorioUsuario:

    def __init__(self, session: Session) -> None:

        self.session = session

    def registrar_hash_pades(
        self,
        sha256: str,
        *,
        scope: str,
        tipo: str | None = None,
        usuario_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
    ) -> bool:
        return registrar_hash_pades(
            self.session,
            sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )

    def obtener_por_email(self, email: str) -> Usuario | None:

        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.email == email))

        return _usuario(u) if u else None

    def obtener(self, usuario_id: uuid.UUID) -> Usuario | None:

        u = self.session.get(orm.Usuario, usuario_id)

        return _usuario(u) if u else None

    def obtener_por_rut(self, rut: str) -> Usuario | None:

        u = self.session.scalar(select(orm.Usuario).where(orm.Usuario.rut == rut))

        return _usuario(u) if u else None

    def crear(self, email: str, nombre: str, hash_contrasena: str) -> Usuario:

        return Usuario(
            id=uuid.uuid4(), email=email, nombre=nombre, password_hash=hash_contrasena
        )

    def eliminar(self, usuario_id: uuid.UUID) -> None:

        u = self.session.get(orm.Usuario, usuario_id)

        if u is not None:

            self.session.delete(u)

            self.session.commit()

    def guardar(self, usuario: Usuario) -> Usuario:

        u = self.session.get(orm.Usuario, usuario.id)

        if u is None:

            u = orm.Usuario(id=usuario.id)

            self.session.add(u)

        u.email = usuario.email

        u.nombre = usuario.nombre

        u.password_hash = usuario.password_hash

        u.activo = usuario.activo

        u.rut = usuario.rut

        u.rut_verificado = usuario.rut_verificado

        u.telefono = usuario.telefono

        u.biometria_verificada = usuario.biometria_verificada

        u.biometria_verificada_en = usuario.biometria_verificada_en

        u.biometria_ruta = usuario.biometria_ruta

        u.biometria_sha256 = usuario.biometria_sha256

        u.biometria_bytes = usuario.biometria_bytes

        u.biometria_ancho = usuario.biometria_ancho

        u.biometria_alto = usuario.biometria_alto

        u.biometria_content_type = usuario.biometria_content_type

        u.biometria_retener_hasta = usuario.biometria_retener_hasta

        u.cedula_verificada = bool(usuario.cedula_verificada)

        u.cedula_verificada_en = usuario.cedula_verificada_en

        u.cedula_ruta = usuario.cedula_ruta

        u.cedula_sha256 = usuario.cedula_sha256

        u.cedula_bytes = usuario.cedula_bytes

        u.cedula_ancho = usuario.cedula_ancho

        u.cedula_alto = usuario.cedula_alto

        u.cedula_content_type = usuario.cedula_content_type

        u.cedula_retener_hasta = usuario.cedula_retener_hasta

        u.cedula_score = usuario.cedula_score

        u.cedula_rut_ocr = usuario.cedula_rut_ocr

        u.antecedentes_verificados = bool(usuario.antecedentes_verificados)

        u.antecedentes_verificados_en = usuario.antecedentes_verificados_en

        u.antecedentes_anotaciones = usuario.antecedentes_anotaciones

        u.antecedentes_score = usuario.antecedentes_score

        u.antecedentes_pades = bool(usuario.antecedentes_pades)

        u.antecedentes_entidad_emisora = usuario.antecedentes_entidad_emisora

        u.antecedentes_fecha_emision = usuario.antecedentes_fecha_emision

        u.antecedentes_sha256 = usuario.antecedentes_sha256

        u.antecedentes_glosa = usuario.antecedentes_glosa

        u.aval_verificado = bool(usuario.aval_verificado)

        u.aval_verificado_en = usuario.aval_verificado_en

        u.aval_score = usuario.aval_score

        u.aval_tipo = usuario.aval_tipo

        u.xp = int(usuario.xp or 0)

        if usuario.perfil is not None:

            if u.perfil is None:

                u.perfil = orm.Perfil(usuario_id=usuario.id)

            u.perfil.edad = usuario.perfil.edad

            u.perfil.tipo_cuenta = usuario.perfil.tipo_cuenta

        self.session.commit()

        self.session.refresh(u)

        return _usuario(u)

class RepositorioXp:

    def __init__(self, session: Session) -> None:

        self.session = session

    def otorgar(self, usuario_id: uuid.UUID, evento: str, puntos: int) -> int:

        if puntos <= 0:

            return 0

        ya = self.session.scalar(
            select(orm.UsuarioXpEvento.id).where(
                orm.UsuarioXpEvento.usuario_id == usuario_id,
                orm.UsuarioXpEvento.evento == evento,
            )
        )

        if ya is not None:

            return 0

        self.session.add(
            orm.UsuarioXpEvento(usuario_id=usuario_id, evento=evento, puntos=puntos)
        )

        u = self.session.get(orm.Usuario, usuario_id)

        if u is None:

            return 0

        u.xp = int(u.xp or 0) + puntos

        self.session.commit()

        return puntos

    def total(self, usuario_id: uuid.UUID) -> int:

        u = self.session.get(orm.Usuario, usuario_id)

        return int(u.xp or 0) if u else 0

def registrar_hash_pades(
    session: Session,
    sha256: str,
    *,
    scope: str,
    tipo: str | None = None,
    usuario_id: uuid.UUID | None = None,
    business_id: uuid.UUID | None = None,
) -> bool:

    existente = session.get(orm.HashDocumentoPades, sha256)
    if existente is not None:
        mismo_usuario = (
            usuario_id is not None and existente.usuario_id == usuario_id
        )
        misma_empresa = (
            business_id is not None and existente.business_id == business_id
        )
        return bool(mismo_usuario or misma_empresa)
    session.add(
        orm.HashDocumentoPades(
            sha256=sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )
    )
    return True

def _like(texto: str) -> str:
    limpio = (
        texto.strip()
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{limpio}%"

def _json_tiene(columna, valor: str):

    return cast(columna, String).like(_like(f'"{valor}"'), escape="\\")

class RepositorioNegocio:

    def __init__(self, session: Session) -> None:

        self.session = session

    def registrar_hash_pades(
        self,
        sha256: str,
        *,
        scope: str,
        tipo: str | None = None,
        usuario_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
    ) -> bool:
        return registrar_hash_pades(
            self.session,
            sha256,
            scope=scope,
            tipo=tipo,
            usuario_id=usuario_id,
            business_id=business_id,
        )

    def obtener(self, negocio_id: uuid.UUID) -> Negocio | None:

        n = self.session.get(orm.EntidadNegocio, negocio_id)

        return _negocio(n) if n else None

    def listar(
        self, filtro: FiltroListado | None = None, limite: int = 100
    ) -> list[Negocio]:

        filtro = filtro or FiltroListado()

        stmt = (
            select(orm.EntidadNegocio)
            .options(*_opciones_lista())
            .order_by(orm.EntidadNegocio.nombre)
        )

        if filtro.categoria:

            stmt = stmt.where(orm.EntidadNegocio.categoria == filtro.categoria)

        if filtro.monto:

            stmt = stmt.where(orm.EntidadNegocio.monto == filtro.monto)

        if filtro.plazo:

            stmt = stmt.where(orm.EntidadNegocio.plazo == filtro.plazo)

        if filtro.industria:

            stmt = stmt.where(_json_tiene(orm.EntidadNegocio.industrias, filtro.industria))

        if filtro.contratacion:

            stmt = stmt.where(
                _json_tiene(orm.EntidadNegocio.contrataciones, filtro.contratacion)
            )

        if filtro.q and filtro.q.strip():

            patron = _like(filtro.q)

            stmt = stmt.where(
                orm.EntidadNegocio.nombre.ilike(patron, escape="\\")
                | orm.EntidadNegocio.direccion.ilike(patron, escape="\\")
                | cast(orm.EntidadNegocio.servicios, String).ilike(patron, escape="\\")
                | cast(orm.EntidadNegocio.referencias, String).ilike(patron, escape="\\")
            )

        return [
            _negocio_lista(n) for n in self.session.scalars(stmt.limit(limite)).unique()
        ]

    def listar_de(self, usuario_id: uuid.UUID) -> list[Negocio]:

        stmt = (
            select(orm.EntidadNegocio)
            .options(joinedload(orm.EntidadNegocio.metricas))
            .where(orm.EntidadNegocio.reclamado_por == usuario_id)
        )

        return [_negocio(n) for n in self.session.scalars(stmt).unique()]

    def listar_completos(self, limite: int = 500) -> list[Negocio]:

        stmt = (
            select(orm.EntidadNegocio)
            .outerjoin(orm.MetricasReputacionNegocio)
            .options(joinedload(orm.EntidadNegocio.metricas))
            .order_by(
                orm.MetricasReputacionNegocio.rater_escaneado_en.is_(None).desc(),
                orm.EntidadNegocio.nombre,
            )
            .limit(max(1, min(limite, 2000)))
        )
        return [_negocio(n) for n in self.session.scalars(stmt).unique()]

    def eliminar(self, negocio_id: uuid.UUID) -> None:

        n = self.session.get(orm.EntidadNegocio, negocio_id)

        if n is None:

            return

        self.session.delete(n)

        self.session.commit()

    def eliminar_de(self, usuario_id: uuid.UUID) -> None:

        stmt = select(orm.EntidadNegocio).where(
            orm.EntidadNegocio.reclamado_por == usuario_id
        )

        for n in list(self.session.scalars(stmt)):

            self.session.delete(n)

        self.session.commit()

    def guardar(self, negocio: Negocio, *, commit: bool = True) -> Negocio:

        if self._rut_lo_tiene_otro(negocio.rut_empresa, negocio.id):

            raise RutEmpresaEnUso()

        n = self.session.get(orm.EntidadNegocio, negocio.id)

        if n is None:

            n = orm.EntidadNegocio(id=negocio.id)

            self.session.add(n)

        n.nombre = negocio.nombre

        n.categoria = negocio.categoria

        n.latitud = negocio.latitud

        n.longitud = negocio.longitud

        n.direccion = negocio.direccion

        n.descripcion = negocio.descripcion

        n.servicios = list(negocio.servicios or ())

        n.industrias = list(negocio.industrias or ())

        n.contrataciones = list(negocio.contrataciones or ())

        n.monto = negocio.monto

        n.plazo = negocio.plazo

        n.referencias = list(negocio.referencias or ())

        n.imagen_url = negocio.imagen_url

        n.logo_url = negocio.logo_url

        n.requiere_nivel = negocio.requiere_nivel

        n.is_claimed = negocio.is_claimed

        n.reclamado_por = negocio.reclamado_por

        n.telefono = negocio.telefono

        n.sitio_web = negocio.sitio_web

        n.rut_empresa = negocio.rut_empresa

        n.docs_empresa = (
            docs_empresa_a_raw(negocio.docs_empresa)
            if negocio.docs_empresa is not None
            else {}
        )

        if negocio.metricas is not None:

            m = negocio.metricas

            if n.metricas is None:

                n.metricas = orm.MetricasReputacionNegocio(
                    business_id=negocio.id, actualizado_en=ahora_utc()
                )

            n.metricas.google_rating_avg = m.google_rating_avg

            n.metricas.google_reviews_count = m.google_reviews_count

            n.metricas.final_score = m.final_score

            n.metricas.rater_escaneado_en = m.rater_escaneado_en

            n.metricas.observables = (
                list(m.observables)
                if isinstance(m.observables, list)
                else None
            )

        try:
            if commit:
                self.session.commit()
            else:
                self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            if _es_rut_empresa_duplicado(exc):
                raise RutEmpresaEnUso() from None
            raise

        if commit:
            self.session.refresh(n)

        return _negocio(n)

    def _rut_lo_tiene_otro(self, rut: str | None, negocio_id: uuid.UUID) -> bool:

        if not rut:

            return False

        stmt = select(orm.EntidadNegocio.id).where(
            orm.EntidadNegocio.rut_empresa == rut,
            orm.EntidadNegocio.id != negocio_id,
        )

        return self.session.scalar(stmt) is not None

def _es_rut_empresa_duplicado(exc: IntegrityError) -> bool:

    orig = getattr(exc, "orig", None)

    diag = getattr(orig, "diag", None)

    if getattr(diag, "constraint_name", None) == "business_entities_rut_empresa_uidx":

        return True

    texto = str(orig or exc).lower()

    return "unique" in texto and "rut_empresa" in texto

class RepositorioTrabajo:

    def __init__(self, session: Session) -> None:

        self.session = session

    def crear(
        self, usuario_id: uuid.UUID, negocio_id: uuid.UUID, token_qr: str
    ) -> Trabajo:

        r = orm.Trabajo(
            usuario_id=usuario_id,
            business_id=negocio_id,
            estado="abierto",
            qr_token=token_qr,
        )

        self.session.add(r)

        self.session.commit()

        self.session.refresh(r)

        return _trabajo(r)

    def obtener(self, trabajo_id: uuid.UUID) -> Trabajo | None:

        r = self.session.get(orm.Trabajo, trabajo_id)

        return _trabajo(r) if r else None

    def obtener_por_qr(self, negocio_id: uuid.UUID, token_qr: str) -> Trabajo | None:

        stmt = select(orm.Trabajo).where(
            orm.Trabajo.business_id == negocio_id, orm.Trabajo.qr_token == token_qr
        )

        r = self.session.scalar(stmt)

        return _trabajo(r) if r else None

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Trabajo]:

        stmt = (
            select(orm.Trabajo)
            .where(orm.Trabajo.usuario_id == usuario_id)
            .order_by(orm.Trabajo.creado_en.desc())
        )

        return [_trabajo(r) for r in self.session.scalars(stmt)]

    def listar_por_negocio(self, negocio_id: uuid.UUID) -> list[Trabajo]:
        stmt = (
            select(orm.Trabajo)
            .where(orm.Trabajo.business_id == negocio_id)
            .order_by(orm.Trabajo.creado_en.desc())
        )
        return [_trabajo(r) for r in self.session.scalars(stmt)]

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]:

        stmt = (
            select(orm.Trabajo.estado, func.count())
            .where(orm.Trabajo.usuario_id == usuario_id)
            .group_by(orm.Trabajo.estado)
        )

        return {
            estado: cantidad for estado, cantidad in self.session.execute(stmt).all()
        }

    def contar_concretados_por_negocios(
        self, negocio_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not negocio_ids:
            return {}
        stmt = (
            select(orm.Trabajo.business_id, func.count())
            .where(
                orm.Trabajo.business_id.in_(negocio_ids),
                orm.Trabajo.estado == "concretado",
            )
            .group_by(orm.Trabajo.business_id)
        )
        return {
            negocio_id: int(cantidad)
            for negocio_id, cantidad in self.session.execute(stmt).all()
        }

    def guardar(self, trabajo: Trabajo) -> Trabajo:

        r = self.session.get(orm.Trabajo, trabajo.id)

        r.estado = trabajo.estado

        self.session.commit()

        self.session.refresh(r)

        return _trabajo(r)

class RepositorioCorreo:
    def __init__(self, session: Session) -> None:
        self.session = session

    def registrar(
        self,
        usuario_id: uuid.UUID,
        business_id: uuid.UUID | None,
        tipo: str,
        destino: str,
        asunto: str,
        cuerpo: str,
        estado: str,
    ) -> None:
        self.session.add(
            orm.MensajeCorreo(
                usuario_id=usuario_id,
                business_id=business_id,
                tipo=tipo,
                destino=destino,
                asunto=asunto[:200],
                cuerpo=cuerpo,
                estado=estado,
            )
        )
        self.session.commit()

class RepositorioCompraInforme:
    def __init__(self, session: Session) -> None:
        self.session = session

    def crear(
        self,
        usuario_id: uuid.UUID,
        business_id: uuid.UUID,
        buy_order: str,
        monto: int,
    ) -> CompraInforme:
        r = orm.CompraInforme(
            usuario_id=usuario_id,
            business_id=business_id,
            buy_order=buy_order[:26],
            monto=int(monto),
            estado="pendiente",
        )
        self.session.add(r)
        self.session.commit()
        self.session.refresh(r)
        return _compra_informe(r)

    def guardar(self, compra: CompraInforme) -> CompraInforme:
        from app.dominio.errores import PagoInformeError
        from app.dominio.pago_informe import ESTADO_AUTORIZADO

        r = self.session.get(orm.CompraInforme, compra.id)
        if r is None:
            raise LookupError("compra_informe")
        r.estado = compra.estado
        r.token = compra.token
        r.response_code = compra.response_code
        r.authorization_code = compra.authorization_code
        r.payment_type_code = compra.payment_type_code
        r.card_last4 = compra.card_last4
        r.error_codigo = compra.error_codigo
        r.error_detalle = (compra.error_detalle or None)
        if r.error_detalle and len(r.error_detalle) > 2000:
            r.error_detalle = r.error_detalle[:2000]
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()

            if compra.estado == ESTADO_AUTORIZADO:
                otra = self.ultima_autorizada(compra.usuario_id, compra.business_id)
                if otra is not None:
                    raise PagoInformeError(
                        "Ya tiene el informe de este proveedor.",
                        codigo="ya_comprado",
                        buy_order=otra.buy_order,
                    ) from exc
            raise
        self.session.refresh(r)
        return _compra_informe(r)

    def obtener_por_token(self, token: str) -> CompraInforme | None:
        stmt = select(orm.CompraInforme).where(orm.CompraInforme.token == token)
        r = self.session.scalars(stmt).first()
        return _compra_informe(r) if r else None

    def obtener_por_buy_order(self, buy_order: str) -> CompraInforme | None:
        stmt = select(orm.CompraInforme).where(
            orm.CompraInforme.buy_order == buy_order
        )
        r = self.session.scalars(stmt).first()
        return _compra_informe(r) if r else None

    def reclamar_para_confirmar(
        self, token: str, usuario_id: uuid.UUID
    ) -> tuple[str, CompraInforme | None]:

        from datetime import datetime, timedelta, timezone

        from sqlalchemy import update

        from app.dominio.pago_informe import (
            ESTADO_AUTORIZADO,
            ESTADO_CONFIRMANDO,
            ESTADO_PENDIENTE,
        )

        token = (token or "").strip()
        stmt = select(orm.CompraInforme).where(orm.CompraInforme.token == token)
        r = self.session.scalars(stmt).first()
        if r is None:
            return ("no", None)
        if r.usuario_id != usuario_id:
            return ("ajena", _compra_informe(r))
        if r.estado == ESTADO_AUTORIZADO:
            return ("ya_ok", _compra_informe(r))
        ahora = datetime.now(timezone.utc)
        stale = False
        if r.estado == ESTADO_CONFIRMANDO:
            ref = r.actualizado_en or r.creado_en
            if ref is not None:
                if ref.tzinfo is None:
                    ref = ref.replace(tzinfo=timezone.utc)
                stale = ref < (ahora - timedelta(seconds=180))
            if not stale:
                return ("en_curso", _compra_informe(r))
        elif r.estado != ESTADO_PENDIENTE:
            return ("estado", _compra_informe(r))

        res = self.session.execute(
            update(orm.CompraInforme)
            .where(
                orm.CompraInforme.id == r.id,
                orm.CompraInforme.estado.in_(
                    [ESTADO_PENDIENTE, ESTADO_CONFIRMANDO]
                ),
            )
            .values(estado=ESTADO_CONFIRMANDO)
        )
        self.session.commit()
        if not res.rowcount:
            r2 = self.session.get(orm.CompraInforme, r.id)
            if r2 and r2.estado == ESTADO_AUTORIZADO:
                return ("ya_ok", _compra_informe(r2))
            return ("en_curso", _compra_informe(r2) if r2 else None)
        self.session.refresh(r)
        return ("ok", _compra_informe(r))

    def tiene_autorizada(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID
    ) -> bool:
        return self.ultima_autorizada(usuario_id, business_id) is not None

    def ultima_autorizada(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID
    ) -> CompraInforme | None:
        from app.dominio.pago_informe import ESTADO_AUTORIZADO

        stmt = (
            select(orm.CompraInforme)
            .where(
                orm.CompraInforme.usuario_id == usuario_id,
                orm.CompraInforme.business_id == business_id,
                orm.CompraInforme.estado == ESTADO_AUTORIZADO,
            )
            .order_by(orm.CompraInforme.creado_en.desc())
            .limit(1)
        )
        r = self.session.scalars(stmt).first()
        return _compra_informe(r) if r else None

    def listar_pendientes_reconciliar(
        self,
        *,
        min_edad_seg: int = 180,
        max_edad_seg: int = 7200,
        limite: int = 25,
    ) -> list[CompraInforme]:

        from datetime import datetime, timedelta, timezone

        from app.dominio.pago_informe import ESTADO_PENDIENTE

        ahora = datetime.now(timezone.utc)
        max_creado = ahora - timedelta(seconds=max(30, min_edad_seg))
        min_creado = ahora - timedelta(seconds=max(min_edad_seg + 1, max_edad_seg))
        stmt = (
            select(orm.CompraInforme)
            .where(
                orm.CompraInforme.estado == ESTADO_PENDIENTE,
                orm.CompraInforme.token.is_not(None),
                orm.CompraInforme.creado_en <= max_creado,
                orm.CompraInforme.creado_en >= min_creado,
            )
            .order_by(orm.CompraInforme.creado_en.asc())
            .limit(max(1, min(100, limite)))
        )
        return [_compra_informe(r) for r in self.session.scalars(stmt).all()]

    def anular_pendientes_abiertos(
        self,
        usuario_id: uuid.UUID,
        business_id: uuid.UUID,
        *,
        excepto_id: uuid.UUID | None = None,
    ) -> int:
        from sqlalchemy import update

        from app.dominio.pago_informe import (
            ESTADO_ANULADO,
            ESTADO_CONFIRMANDO,
            ESTADO_PENDIENTE,
        )

        cond = [
            orm.CompraInforme.usuario_id == usuario_id,
            orm.CompraInforme.business_id == business_id,
            orm.CompraInforme.estado.in_([ESTADO_PENDIENTE, ESTADO_CONFIRMANDO]),
        ]
        if excepto_id is not None:
            cond.append(orm.CompraInforme.id != excepto_id)
        res = self.session.execute(
            update(orm.CompraInforme)
            .where(*cond)
            .values(
                estado=ESTADO_ANULADO,
                error_codigo="pendiente_reemplazado",
                error_detalle="Reemplazado por un nuevo intento de pago",
            )
        )
        self.session.commit()
        return int(res.rowcount or 0)

    def resumen_mes(self, usuario_id: uuid.UUID, mes_clave: str) -> tuple[int, int]:

        from sqlalchemy import extract, func

        from app.dominio.pago_informe import ESTADO_AUTORIZADO

        try:
            anio, mes = [int(x) for x in mes_clave.split("-", 1)]
        except (TypeError, ValueError):
            return (0, 0)
        stmt = select(
            func.count(orm.CompraInforme.id),
            func.coalesce(func.sum(orm.CompraInforme.monto), 0),
        ).where(
            orm.CompraInforme.usuario_id == usuario_id,
            orm.CompraInforme.estado == ESTADO_AUTORIZADO,
            extract("year", orm.CompraInforme.creado_en) == anio,
            extract("month", orm.CompraInforme.creado_en) == mes,
        )
        row = self.session.execute(stmt).one()
        return (int(row[0] or 0), int(row[1] or 0))

def _compra_publicacion(r: orm.CompraPublicacion) -> CompraPublicacion:
    return CompraPublicacion(
        id=r.id,
        usuario_id=r.usuario_id,
        business_id=r.business_id,
        buy_order=r.buy_order,
        monto=int(r.monto),
        estado=r.estado,
        token=r.token,
        response_code=r.response_code,
        authorization_code=r.authorization_code,
        payment_type_code=r.payment_type_code,
        card_last4=r.card_last4,
        error_codigo=r.error_codigo,
        error_detalle=r.error_detalle,
        creado_en=r.creado_en,
        actualizado_en=r.actualizado_en,
    )

class RepositorioCompraPublicacion:
    def __init__(self, session: Session) -> None:
        self.session = session

    def crear(
        self, usuario_id: uuid.UUID, buy_order: str, monto: int
    ) -> CompraPublicacion:
        r = orm.CompraPublicacion(
            usuario_id=usuario_id,
            business_id=None,
            buy_order=buy_order[:26],
            monto=int(monto),
            estado="pendiente",
        )
        self.session.add(r)
        self.session.commit()
        self.session.refresh(r)
        return _compra_publicacion(r)

    def guardar(self, compra: CompraPublicacion) -> CompraPublicacion:
        r = self.session.get(orm.CompraPublicacion, compra.id)
        if r is None:
            raise LookupError("compra_publicacion")
        r.estado = compra.estado
        r.business_id = compra.business_id
        r.token = compra.token
        r.response_code = compra.response_code
        r.authorization_code = compra.authorization_code
        r.payment_type_code = compra.payment_type_code
        r.card_last4 = compra.card_last4
        r.error_codigo = compra.error_codigo
        r.error_detalle = (compra.error_detalle or None)
        if r.error_detalle and len(r.error_detalle) > 2000:
            r.error_detalle = r.error_detalle[:2000]
        self.session.commit()
        self.session.refresh(r)
        return _compra_publicacion(r)

    def obtener_por_token(self, token: str) -> CompraPublicacion | None:
        stmt = select(orm.CompraPublicacion).where(
            orm.CompraPublicacion.token == token
        )
        r = self.session.scalars(stmt).first()
        return _compra_publicacion(r) if r else None

    def obtener_por_buy_order(self, buy_order: str) -> CompraPublicacion | None:
        stmt = select(orm.CompraPublicacion).where(
            orm.CompraPublicacion.buy_order == buy_order
        )
        r = self.session.scalars(stmt).first()
        return _compra_publicacion(r) if r else None

    def cupon_libre(self, usuario_id: uuid.UUID) -> CompraPublicacion | None:

        return self.cupon_listo_alta(usuario_id)

    def cupon_listo_alta(self, usuario_id: uuid.UUID) -> CompraPublicacion | None:

        from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO

        stmt = (
            select(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.usuario_id == usuario_id,
                orm.CompraPublicacion.estado.in_(
                    [ESTADO_AUTORIZADO, ESTADO_RESERVADO]
                ),
                orm.CompraPublicacion.business_id.is_(None),
            )
            .order_by(orm.CompraPublicacion.creado_en.desc())
            .limit(1)
        )
        r = self.session.scalars(stmt).first()
        return _compra_publicacion(r) if r else None

    def reservar_para_alta(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        *,
        commit: bool = True,
    ) -> CompraPublicacion | None:

        from sqlalchemy import update

        from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO

        orden = (buy_order or "").strip()
        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.buy_order == orden,
                orm.CompraPublicacion.usuario_id == usuario_id,
                orm.CompraPublicacion.estado == ESTADO_AUTORIZADO,
                orm.CompraPublicacion.business_id.is_(None),
            )
            .values(estado=ESTADO_RESERVADO)
        )
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        if res.rowcount:
            return self.obtener_por_buy_order(orden)
        actual = self.obtener_por_buy_order(orden)
        if (
            actual is not None
            and actual.usuario_id == usuario_id
            and actual.estado == ESTADO_RESERVADO
            and actual.business_id is None
        ):
            return actual
        return None

    def liberar_reserva(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        *,
        commit: bool = True,
    ) -> CompraPublicacion | None:

        from sqlalchemy import update

        from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO

        orden = (buy_order or "").strip()
        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.buy_order == orden,
                orm.CompraPublicacion.usuario_id == usuario_id,
                orm.CompraPublicacion.estado == ESTADO_RESERVADO,
                orm.CompraPublicacion.business_id.is_(None),
            )
            .values(estado=ESTADO_AUTORIZADO)
        )
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        if res.rowcount:
            return self.obtener_por_buy_order(orden)
        return None

    def liberar_reservas_stale(self, *, max_edad_seg: int = 180) -> int:

        from datetime import datetime, timedelta, timezone

        from sqlalchemy import update

        from app.dominio.pago_publicacion import ESTADO_AUTORIZADO, ESTADO_RESERVADO

        limite = datetime.now(timezone.utc) - timedelta(seconds=max(60, max_edad_seg))
        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.estado == ESTADO_RESERVADO,
                orm.CompraPublicacion.business_id.is_(None),
                orm.CompraPublicacion.actualizado_en < limite,
            )
            .values(
                estado=ESTADO_AUTORIZADO,
                error_codigo="reserva_expirada",
                error_detalle="Reserva de alta expiró sin consumir",
            )
        )
        self.session.commit()
        return int(res.rowcount or 0)

    def consumir_atomico(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        business_id: uuid.UUID,
        *,
        commit: bool = True,
    ) -> CompraPublicacion | None:

        from sqlalchemy import update

        from app.dominio.pago_publicacion import (
            ESTADO_AUTORIZADO,
            ESTADO_CONSUMIDO,
            ESTADO_RESERVADO,
        )

        orden = (buy_order or "").strip()
        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.buy_order == orden,
                orm.CompraPublicacion.usuario_id == usuario_id,
                orm.CompraPublicacion.estado.in_(
                    [ESTADO_RESERVADO, ESTADO_AUTORIZADO]
                ),
                orm.CompraPublicacion.business_id.is_(None),
            )
            .values(business_id=business_id, estado=ESTADO_CONSUMIDO)
        )
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        if res.rowcount:
            return self.obtener_por_buy_order(orden)
        actual = self.obtener_por_buy_order(orden)
        if (
            actual is not None
            and actual.usuario_id == usuario_id
            and actual.business_id == business_id
            and actual.estado == ESTADO_CONSUMIDO
        ):
            return actual
        return None

    def anular_pendientes_abiertos(
        self, usuario_id: uuid.UUID, *, excepto_id=None
    ) -> int:
        from sqlalchemy import update

        from app.dominio.pago_publicacion import (
            ESTADO_ANULADO,
            ESTADO_CONFIRMANDO,
            ESTADO_PENDIENTE,
        )

        cond = [
            orm.CompraPublicacion.usuario_id == usuario_id,
            orm.CompraPublicacion.business_id.is_(None),
            orm.CompraPublicacion.estado.in_([ESTADO_PENDIENTE, ESTADO_CONFIRMANDO]),
        ]
        if excepto_id is not None:
            cond.append(orm.CompraPublicacion.id != excepto_id)
        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(*cond)
            .values(
                estado=ESTADO_ANULADO,
                error_codigo="pendiente_reemplazado",
                error_detalle="Reemplazado por un nuevo intento de pago",
            )
        )
        self.session.commit()
        return int(res.rowcount or 0)

    def reclamar_para_confirmar(
        self, token: str, usuario_id: uuid.UUID
    ) -> tuple[str, CompraPublicacion | None]:
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import update

        from app.dominio.pago_publicacion import (
            ESTADO_AUTORIZADO,
            ESTADO_CONFIRMANDO,
            ESTADO_PENDIENTE,
        )

        token = (token or "").strip()
        stmt = select(orm.CompraPublicacion).where(
            orm.CompraPublicacion.token == token
        )
        r = self.session.scalars(stmt).first()
        if r is None:
            return ("no", None)
        if r.usuario_id != usuario_id:
            return ("ajena", _compra_publicacion(r))
        if r.estado == ESTADO_AUTORIZADO:
            return ("ya_ok", _compra_publicacion(r))
        ahora = datetime.now(timezone.utc)
        stale = False
        if r.estado == ESTADO_CONFIRMANDO:
            ref = r.actualizado_en or r.creado_en
            if ref is not None:
                if ref.tzinfo is None:
                    ref = ref.replace(tzinfo=timezone.utc)
                stale = ref < (ahora - timedelta(seconds=180))
            if not stale:
                return ("en_curso", _compra_publicacion(r))
        elif r.estado != ESTADO_PENDIENTE:
            return ("estado", _compra_publicacion(r))

        res = self.session.execute(
            update(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.id == r.id,
                orm.CompraPublicacion.estado.in_(
                    [ESTADO_PENDIENTE, ESTADO_CONFIRMANDO]
                ),
            )
            .values(estado=ESTADO_CONFIRMANDO)
        )
        self.session.commit()
        if not res.rowcount:
            r2 = self.session.get(orm.CompraPublicacion, r.id)
            if r2 and r2.estado == ESTADO_AUTORIZADO:
                return ("ya_ok", _compra_publicacion(r2))
            return ("en_curso", _compra_publicacion(r2) if r2 else None)
        self.session.refresh(r)
        return ("ok", _compra_publicacion(r))

    def listar_pendientes_reconciliar(
        self,
        *,
        min_edad_seg: int = 180,
        max_edad_seg: int = 7200,
        limite: int = 25,
    ) -> list[CompraPublicacion]:
        from datetime import datetime, timedelta, timezone

        from app.dominio.pago_publicacion import ESTADO_PENDIENTE

        ahora = datetime.now(timezone.utc)
        max_creado = ahora - timedelta(seconds=max(30, min_edad_seg))
        min_creado = ahora - timedelta(seconds=max(min_edad_seg + 1, max_edad_seg))
        stmt = (
            select(orm.CompraPublicacion)
            .where(
                orm.CompraPublicacion.estado == ESTADO_PENDIENTE,
                orm.CompraPublicacion.token.is_not(None),
                orm.CompraPublicacion.creado_en <= max_creado,
                orm.CompraPublicacion.creado_en >= min_creado,
            )
            .order_by(orm.CompraPublicacion.creado_en.asc())
            .limit(max(1, min(100, limite)))
        )
        return [_compra_publicacion(r) for r in self.session.scalars(stmt).all()]
