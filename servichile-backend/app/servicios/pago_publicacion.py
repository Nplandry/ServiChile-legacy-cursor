

from __future__ import annotations

import logging
import secrets
import uuid
from urllib.parse import urlparse

from app.dominio.entidades import Usuario
from app.dominio.errores import PagoPublicacionError, PublicacionSinPago
from app.dominio.pago_publicacion import (
    ESTADO_ANULADO,
    ESTADO_AUTORIZADO,
    ESTADO_CONSUMIDO,
    ESTADO_ERROR,
    ESTADO_PENDIENTE,
    ESTADO_RESERVADO,
    ESTADO_RECHAZADO,
    PRECIO_PUBLICACION_CLP,
    CanalReclamoPublicacion,
    CatalogoPagoPublicacion,
    CompraPublicacion,
    ConfirmacionPagoPublicacion,
    InicioPagoPublicacion,
    formato_monto_clp,
)
from app.dominio.puertos import (
    EnviadorPlataforma,
    MensajeSaliente,
    PasarelaWebpay,
    RepositorioComprasPublicacion,
    RepositorioUsuarios,
)

log = logging.getLogger(__name__)

class ServicioPagoPublicacion:
    def __init__(
        self,
        compras: RepositorioComprasPublicacion,
        pasarela: PasarelaWebpay,
        *,
        return_url: str,
        reclamo_email: str,
        reclamo_whatsapp: str,
        monto: int = PRECIO_PUBLICACION_CLP,
        origenes_permitidos: list[str] | None = None,
        usuarios: RepositorioUsuarios | None = None,
        enviador: EnviadorPlataforma | None = None,
    ) -> None:
        self.compras = compras
        self.pasarela = pasarela
        self.return_url = return_url.rstrip()
        self.reclamo_email = reclamo_email.strip()
        self.reclamo_whatsapp = reclamo_whatsapp.strip()
        self.monto = int(monto)
        self.origenes_permitidos = self._expandir_origenes(origenes_permitidos or [])
        self.usuarios = usuarios
        self.enviador = enviador

    @staticmethod
    def _expandir_origenes(origenes: list[str]) -> set[str]:
        base = {str(o).rstrip("/").lower() for o in origenes if o}
        extras: set[str] = set()
        for o in list(base):
            extras.add(o.replace("://localhost", "://127.0.0.1"))
            extras.add(o.replace("://127.0.0.1", "://localhost"))
        return base | extras

    def reclamo_para(self, buy_order: str) -> CanalReclamoPublicacion:
        email = self.reclamo_email or "pagos@servichile.cl"
        whatsapp = self.reclamo_whatsapp or "+56900000000"
        orden = (buy_order or "—").strip() or "—"
        return CanalReclamoPublicacion(
            email=email,
            whatsapp=whatsapp,
            instruccion=(
                f"Si el cobro de publicación falló, reclame con la orden {orden} "
                f"a {email} o WhatsApp {whatsapp}."
            ),
        )

    def catalogo(self) -> CatalogoPagoPublicacion:
        return CatalogoPagoPublicacion(monto=self.monto)

    def validar_return_url(self, return_url: str | None) -> str | None:
        if not return_url or not str(return_url).strip():
            return None
        raw = str(return_url).strip()
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise PagoPublicacionError(
                "return_url inválida.", codigo="return_url_invalida"
            )
        origen = f"{parsed.scheme}://{parsed.netloc}".lower()
        if self.origenes_permitidos and origen not in self.origenes_permitidos:
            raise PagoPublicacionError(
                "return_url no está permitida.",
                codigo="return_url_no_permitida",
            )
        return raw

    def _normalizar_retorno(self, return_url: str | None) -> str:
        candidato = (return_url or "").strip() or (self.return_url or "").strip()
        if not candidato:
            raise PagoPublicacionError(
                "Falta return_url / PUBLIC_FRONTEND_URL para Webpay.",
                codigo="return_url_ausente",
            )
        if "pago=retorno" not in candidato:
            sep = "&" if "?" in candidato else "?"
            candidato = f"{candidato}{sep}pago=retorno"
        if "producto=publicacion" not in candidato:
            candidato = f"{candidato}&producto=publicacion"
        return candidato

    def _buy_order(self) -> str:
        return ("SCP" + secrets.token_hex(10))[:26]

    def _url_formulario(self, token: str) -> str:
        fn = getattr(self.pasarela, "url_formulario", None)
        if callable(fn):
            return str(fn(token) or "").strip() or "http://localhost/tbk-mock"
        return "http://localhost/tbk-mock"

    def iniciar(
        self, usuario: Usuario, return_url: str | None = None
    ) -> InicioPagoPublicacion:
        cupon = self.compras.cupon_libre(usuario.id)
        if cupon is not None:
            raise PagoPublicacionError(
                "Ya tiene un pago de publicación listo. Complete la creación de la ficha.",
                codigo="cupon_disponible",
                buy_order=cupon.buy_order,
            )

        self.compras.anular_pendientes_abiertos(usuario.id)
        retorno = self._normalizar_retorno(return_url)
        buy_order = self._buy_order()
        compra = self.compras.crear(usuario.id, buy_order, self.monto)
        try:
            tx = self.pasarela.crear(
                buy_order, str(usuario.id), self.monto, retorno
            )
        except Exception as e:
            from app.dominio.errores import PagoInformeError

            if isinstance(e, PagoInformeError):
                compra.estado = ESTADO_ERROR
                compra.error_codigo = e.codigo
                compra.error_detalle = e.mensaje
                self.compras.guardar(compra)
                raise PagoPublicacionError(
                    e.mensaje, codigo=e.codigo, buy_order=buy_order
                ) from e
            compra.estado = ESTADO_ERROR
            compra.error_codigo = "tbk_create_ex"
            compra.error_detalle = str(e)[:500]
            self.compras.guardar(compra)
            raise PagoPublicacionError(
                "Error inesperado al iniciar el pago de publicación.",
                codigo="tbk_create_ex",
                buy_order=buy_order,
            ) from e
        compra.token = tx.token
        compra.estado = ESTADO_PENDIENTE
        self.compras.guardar(compra)
        return InicioPagoPublicacion(
            buy_order=buy_order,
            token=tx.token,
            url=tx.url,
            monto=self.monto,
            reclamo=self.reclamo_para(buy_order),
        )

    def _restaurar_pendiente(self, compra) -> None:
        compra.estado = ESTADO_PENDIENTE
        compra.error_codigo = None
        compra.error_detalle = None
        self.compras.guardar(compra)

    def _aplicar_commit_tbk(self, compra, token: str, *, reintentable: bool = False):
        from app.dominio.errores import PagoInformeError

        try:
            tx = self.pasarela.confirmar(token)
        except PagoInformeError as e:
            if reintentable and e.codigo in ("tbk_commit_red", "tbk_commit_http"):
                self._restaurar_pendiente(compra)
            else:
                compra.estado = ESTADO_ERROR
                compra.error_codigo = e.codigo
                compra.error_detalle = e.mensaje
                self.compras.guardar(compra)
            raise PagoPublicacionError(
                e.mensaje, codigo=e.codigo, buy_order=compra.buy_order
            ) from e

        compra.response_code = tx.response_code
        compra.authorization_code = tx.authorization_code
        compra.payment_type_code = tx.payment_type_code
        compra.card_last4 = tx.card_last4
        status = (tx.status or "").upper()
        if tx.response_code == 0:
            compra.estado = ESTADO_AUTORIZADO
            compra.error_codigo = None
            compra.error_detalle = None
        elif status in ("ABORTED", "FAILED"):
            compra.estado = ESTADO_RECHAZADO
            compra.error_codigo = "tbk_rechazado"
            compra.error_detalle = tx.detalle or f"response_code={tx.response_code}"
        elif reintentable and status in ("", "INITIALIZED", "PENDING"):
            self._restaurar_pendiente(compra)
            raise PagoPublicacionError(
                "Transacción Webpay aún no lista para commit.",
                codigo="tbk_aun_pendiente",
                buy_order=compra.buy_order,
            )
        else:
            compra.estado = ESTADO_RECHAZADO
            compra.error_codigo = "tbk_no_autorizado"
            compra.error_detalle = (
                tx.detalle or f"status={tx.status} response_code={tx.response_code}"
            )
        self.compras.guardar(compra)
        return compra

    def _respuesta(self, compra) -> ConfirmacionPagoPublicacion:
        autorizado = compra.estado in (
            ESTADO_AUTORIZADO,
            ESTADO_RESERVADO,
            ESTADO_CONSUMIDO,
        )
        consumido = compra.estado == ESTADO_CONSUMIDO or compra.business_id is not None
        return ConfirmacionPagoPublicacion(
            buy_order=compra.buy_order,
            estado=compra.estado,
            autorizado=autorizado,
            monto=compra.monto,
            response_code=compra.response_code,
            authorization_code=compra.authorization_code,
            error_codigo=compra.error_codigo,
            error_detalle=compra.error_detalle,
            reclamo=self.reclamo_para(compra.buy_order),
            business_id=compra.business_id,
            consumido=consumido,
        )

    def _avisar_cupon_listo(self, compra) -> None:

        if compra.estado != ESTADO_AUTORIZADO:
            return
        if self.usuarios is None or self.enviador is None:
            return
        if not self.enviador.disponible():
            return
        usuario = self.usuarios.obtener(compra.usuario_id)
        if usuario is None or not (usuario.email or "").strip():
            return
        precio = formato_monto_clp(compra.monto or self.monto)
        try:
            self.enviador.enviar(
                MensajeSaliente(
                    destino=usuario.email.strip(),
                    asunto="ServiChile: pago de publicación autorizado",
                    cuerpo=(
                        f"Su pago de publicación ({precio}) quedó autorizado.\n"
                        f"Orden: {compra.buy_order}\n\n"
                        "Entre a Perfil y complete la ficha de empresa para "
                        "usar el cupón. El cupón es de un solo uso.\n"
                    ),
                )
            )
        except Exception:
            log.info(
                "No se pudo avisar cupón publicación %s",
                compra.buy_order,
                exc_info=True,
            )

    def confirmar(self, usuario: Usuario, token: str) -> ConfirmacionPagoPublicacion:
        token = (token or "").strip()
        if len(token) < 8:
            raise PagoPublicacionError(
                "Token de pago inválido o ausente.", codigo="token_invalido"
            )
        marca, compra = self.compras.reclamar_para_confirmar(token, usuario.id)
        if marca == "no" or compra is None:
            raise PagoPublicacionError(
                "No encontramos esta compra de publicación.",
                codigo="compra_no_encontrada",
            )
        if marca == "ajena":
            raise PagoPublicacionError(
                "Esta compra pertenece a otra cuenta.",
                codigo="compra_ajena",
                buy_order=compra.buy_order,
            )
        if marca == "ya_ok":
            return self._respuesta(compra)
        if marca == "en_curso":
            raise PagoPublicacionError(
                "La confirmación ya está en curso. Espere unos segundos.",
                codigo="confirmacion_en_curso",
                buy_order=compra.buy_order,
            )
        if marca == "estado":
            raise PagoPublicacionError(
                "Esta compra no se puede confirmar en su estado actual.",
                codigo="estado_invalido",
                buy_order=compra.buy_order,
            )
        compra = self._aplicar_commit_tbk(compra, token)
        if compra.estado == ESTADO_AUTORIZADO:
            self._avisar_cupon_listo(compra)
        return self._respuesta(compra)

    def recuperar(
        self, usuario: Usuario, buy_order: str
    ) -> ConfirmacionPagoPublicacion:
        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoPublicacionError(
                "Compra no encontrada para recuperar.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        if compra.estado == ESTADO_AUTORIZADO:
            return self._respuesta(compra)
        if not compra.token:
            raise PagoPublicacionError(
                "Esta orden no tiene token Webpay para recuperar.",
                codigo="sin_token",
                buy_order=compra.buy_order,
            )
        return self.confirmar(usuario, compra.token)

    def marcar_anulado(
        self, usuario: Usuario, buy_order: str, motivo: str
    ) -> ConfirmacionPagoPublicacion:
        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoPublicacionError(
                "Compra no encontrada para anular.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        if compra.estado == ESTADO_AUTORIZADO:
            return self._respuesta(compra)
        compra.estado = ESTADO_ANULADO
        compra.error_codigo = "tbk_anulado"
        compra.error_detalle = (motivo or "Usuario canceló en Webpay")[:500]
        self.compras.guardar(compra)
        return self._respuesta(compra)

    def consultar(
        self, usuario: Usuario, buy_order: str
    ) -> ConfirmacionPagoPublicacion:
        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoPublicacionError(
                "Compra no encontrada.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        return self._respuesta(compra)

    def cupon_disponible(self, usuario: Usuario) -> ConfirmacionPagoPublicacion | None:
        cupon = self.compras.cupon_listo_alta(usuario.id)
        return self._respuesta(cupon) if cupon else None

    def listo_para_alta(self, buy_order_estado: str, *, consumido: bool) -> bool:

        if consumido:
            return False
        return buy_order_estado in (ESTADO_AUTORIZADO, ESTADO_RESERVADO)

    def reservar_para_alta(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        *,
        commit: bool = True,
    ) -> CompraPublicacion:

        compra = self.compras.reservar_para_alta(
            usuario_id, buy_order, commit=commit
        )
        if compra is None:
            raise PublicacionSinPago(
                "El pago de publicación no está listo o ya fue usado."
            )
        return compra

    def liberar_reserva(
        self, usuario_id: uuid.UUID, buy_order: str, *, commit: bool = True
    ) -> None:
        self.compras.liberar_reserva(usuario_id, buy_order, commit=commit)

    def consumir_para_publicar(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        business_id: uuid.UUID,
        *,
        commit: bool = True,
    ) -> CompraPublicacion:

        orden = (buy_order or "").strip()
        compra = self.compras.consumir_atomico(
            usuario_id, orden, business_id, commit=commit
        )
        if compra is None:
            raise PublicacionSinPago(
                "El pago de publicación no está listo o ya fue usado."
            )
        return compra

    def reconciliar_pendientes(
        self,
        *,
        min_edad_seg: int = 180,
        max_edad_seg: int = 7200,
        limite: int = 25,
    ) -> int:
        liberadas = self.compras.liberar_reservas_stale(max_edad_seg=180)
        if liberadas:
            log.info(
                "Reconciliación publicación: %s reservas stale liberadas.", liberadas
            )
        pendientes = self.compras.listar_pendientes_reconciliar(
            min_edad_seg=min_edad_seg,
            max_edad_seg=max_edad_seg,
            limite=limite,
        )
        cerrados = 0
        for compra in pendientes:
            token = (compra.token or "").strip()
            if len(token) < 8:
                continue
            marca, reclamada = self.compras.reclamar_para_confirmar(
                token, compra.usuario_id
            )
            if marca != "ok" or reclamada is None:
                continue
            try:
                actualizada = self._aplicar_commit_tbk(
                    reclamada, token, reintentable=True
                )
                if actualizada.estado == ESTADO_AUTORIZADO:
                    self._avisar_cupon_listo(actualizada)
                    cerrados += 1
                elif actualizada.estado == ESTADO_RECHAZADO:
                    cerrados += 1
            except PagoPublicacionError:
                continue
            except Exception:
                try:
                    self._restaurar_pendiente(reclamada)
                except Exception:
                    log.exception(
                        "No se pudo restaurar pendiente publicación %s",
                        getattr(reclamada, "buy_order", None),
                    )
                continue
        return cerrados
