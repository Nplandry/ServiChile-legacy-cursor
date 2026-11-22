

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.dominio.entidades import Usuario
from app.dominio.errores import InformeSinCompra, NegocioNoEncontrado, PagoInformeError
from app.dominio.pago_informe import (
    ESTADO_ANULADO,
    ESTADO_AUTORIZADO,
    ESTADO_ERROR,
    ESTADO_PENDIENTE,
    ESTADO_RECHAZADO,
    PRECIO_INFORME_CLP,
    CanalReclamo,
    CatalogoPagoInforme,
    ConfirmacionPagoInforme,
    InicioPagoInforme,
    ResumenComprasInforme,
)
from app.dominio.puertos import (
    PasarelaWebpay,
    RepositorioComprasInforme,
    RepositorioNegocios,
    RepositorioUsuarios,
)
from app.servicios.radar_comercial import ServicioRadarComercial

_PRINT_TTL_SEG = 3600

class ServicioPagoInforme:
    def __init__(
        self,
        compras: RepositorioComprasInforme,
        negocios: RepositorioNegocios,
        pasarela: PasarelaWebpay,
        radar: ServicioRadarComercial,
        *,
        return_url: str,
        reclamo_email: str,
        reclamo_whatsapp: str,
        monto: int = PRECIO_INFORME_CLP,
        origenes_permitidos: list[str] | None = None,
        print_secret: str = "",
        usuarios: RepositorioUsuarios | None = None,
    ) -> None:
        self.compras = compras
        self.negocios = negocios
        self.pasarela = pasarela
        self.radar = radar
        self.usuarios = usuarios
        self.return_url = return_url.rstrip()
        self.reclamo_email = reclamo_email.strip()
        self.reclamo_whatsapp = reclamo_whatsapp.strip()
        self.monto = int(monto)
        self.origenes_permitidos = self._expandir_origenes(origenes_permitidos or [])
        self.print_secret = (print_secret or "").strip()

    @staticmethod
    def _expandir_origenes(origenes: list[str]) -> set[str]:
        base = {str(o).rstrip("/").lower() for o in origenes if o}
        extras: set[str] = set()
        for o in list(base):
            extras.add(o.replace("://localhost", "://127.0.0.1"))
            extras.add(o.replace("://127.0.0.1", "://localhost"))
        return base | extras

    def reclamo_para(self, buy_order: str) -> CanalReclamo:
        email = self.reclamo_email or "pagos@servichile.cl"
        whatsapp = self.reclamo_whatsapp or "+56900000000"
        orden = (buy_order or "—").strip() or "—"
        instruccion = (
            f"Si el cobro falló o no recibió el informe, reclame con la orden "
            f"{orden} a {email} o WhatsApp {whatsapp}. "
            "Indique fecha, monto y correo de su cuenta ServiChile."
        )
        return CanalReclamo(email=email, whatsapp=whatsapp, instruccion=instruccion)

    def catalogo(self) -> CatalogoPagoInforme:
        return CatalogoPagoInforme(monto=self.monto)

    def resumen_usuario(self, usuario: Usuario) -> ResumenComprasInforme:
        ahora = datetime.now(timezone.utc)
        mes = f"{ahora.year:04d}-{ahora.month:02d}"
        n, gastado = self.compras.resumen_mes(usuario.id, mes)
        return ResumenComprasInforme(
            autorizadas_mes=n,
            gastado_mes=gastado,
            monto_unitario=self.monto,
        )

    def validar_return_url(self, return_url: str | None) -> str | None:
        if not return_url or not str(return_url).strip():
            return None
        raw = str(return_url).strip()
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise PagoInformeError(
                "return_url inválida.", codigo="return_url_invalida"
            )
        origen = f"{parsed.scheme}://{parsed.netloc}".lower()
        if self.origenes_permitidos and origen not in self.origenes_permitidos:
            raise PagoInformeError(
                "return_url no está permitida.",
                codigo="return_url_no_permitida",
            )
        return raw

    def _normalizar_retorno(self, return_url: str | None) -> str:
        candidato = (return_url or "").strip() or (self.return_url or "").strip()
        if not candidato:
            raise PagoInformeError(
                "Falta return_url / PUBLIC_FRONTEND_URL para Webpay.",
                codigo="return_url_ausente",
            )
        if "pago=retorno" not in candidato:
            sep = "&" if "?" in candidato else "?"
            candidato = f"{candidato}{sep}pago=retorno"
        return candidato

    def _buy_order(self) -> str:
        return ("SCI" + secrets.token_hex(10))[:26]

    def _url_formulario(self, token: str) -> str:
        fn = getattr(self.pasarela, "url_formulario", None)
        if callable(fn):
            return str(fn(token))
        host = getattr(self.pasarela, "host", None) or "https://webpay3gint.transbank.cl"
        return f"{str(host).rstrip('/')}/webpayserver/initTransaction"

    def tiene_acceso_informe(self, usuario: Usuario, business_id: uuid.UUID) -> bool:
        negocio = self.negocios.obtener(business_id)
        if negocio is None:
            return False
        if negocio.reclamado_por is not None and negocio.reclamado_por == usuario.id:
            return True
        return self.compras.tiene_autorizada(usuario.id, business_id)

    def exigir_acceso_informe(self, usuario: Usuario, business_id: uuid.UUID) -> None:
        if self.negocios.obtener(business_id) is None:
            raise NegocioNoEncontrado()
        if not self.tiene_acceso_informe(usuario, business_id):
            raise InformeSinCompra()

    def emitir_print_token(self, usuario: Usuario, compra) -> str | None:
        if compra.estado != ESTADO_AUTORIZADO or not self.print_secret:
            return None
        exp = int(time.time()) + _PRINT_TTL_SEG
        msg = f"{usuario.id}:{compra.business_id}:{compra.buy_order}:{exp}"
        sig = hmac.new(
            self.print_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:40]
        return f"{exp}.{compra.buy_order}.{sig}"

    def verificar_print_token(
        self, usuario: Usuario, business_id: uuid.UUID, print_token: str
    ) -> ConfirmacionPagoInforme:
        raw = (print_token or "").strip()
        partes = raw.split(".")
        if len(partes) != 3 or not self.print_secret:
            raise PagoInformeError(
                "Token de impresión inválido.", codigo="print_token_invalido"
            )
        try:
            exp = int(partes[0])
        except ValueError as e:
            raise PagoInformeError(
                "Token de impresión inválido.", codigo="print_token_invalido"
            ) from e
        if exp < int(time.time()):
            raise PagoInformeError(
                "Token de impresión expirado. Vuelva a abrir el informe.",
                codigo="print_token_expirado",
            )
        buy_order = partes[1]
        compra = self.compras.obtener_por_buy_order(buy_order)
        if (
            compra is None
            or compra.usuario_id != usuario.id
            or compra.business_id != business_id
            or compra.estado != ESTADO_AUTORIZADO
        ):
            raise InformeSinCompra()
        msg = f"{usuario.id}:{compra.business_id}:{compra.buy_order}:{exp}"
        sig = hmac.new(
            self.print_secret.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:40]
        candidato = f"{exp}.{compra.buy_order}.{sig}"
        if not hmac.compare_digest(candidato, raw):
            raise PagoInformeError(
                "Token de impresión no válido.", codigo="print_token_invalido"
            )
        return self._respuesta(compra, usuario, ya_ok=True)

    def reentregar(
        self, usuario: Usuario, business_id: uuid.UUID
    ) -> ConfirmacionPagoInforme:

        if self.negocios.obtener(business_id) is None:
            raise NegocioNoEncontrado()
        compra = self.compras.ultima_autorizada(usuario.id, business_id)
        if compra is None:
            raise InformeSinCompra()
        return self._respuesta(compra, usuario, ya_ok=True)

    def recuperar(
        self, usuario: Usuario, buy_order: str
    ) -> ConfirmacionPagoInforme:

        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoInformeError(
                "Compra no encontrada para recuperar.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        if compra.estado == ESTADO_AUTORIZADO:
            return self._respuesta(compra, usuario, ya_ok=True)
        if not compra.token:
            raise PagoInformeError(
                "Esta orden no tiene token Webpay para recuperar.",
                codigo="sin_token",
                buy_order=compra.buy_order,
            )
        return self.confirmar(usuario, compra.token)

    def iniciar(
        self,
        usuario: Usuario,
        business_id: uuid.UUID,
        return_url: str | None = None,
    ) -> InicioPagoInforme:
        if self.negocios.obtener(business_id) is None:
            raise NegocioNoEncontrado()
        if self.compras.tiene_autorizada(usuario.id, business_id):
            raise PagoInformeError(
                "Ya tiene el informe de este proveedor.",
                codigo="ya_comprado",
            )

        self.compras.anular_pendientes_abiertos(usuario.id, business_id)
        retorno = self._normalizar_retorno(return_url)
        buy_order = self._buy_order()
        compra = self.compras.crear(
            usuario.id, business_id, buy_order, self.monto
        )
        try:
            tx = self.pasarela.crear(
                buy_order,
                str(usuario.id),
                self.monto,
                retorno,
            )
        except PagoInformeError as e:
            compra.estado = ESTADO_ERROR
            compra.error_codigo = e.codigo
            compra.error_detalle = e.mensaje
            self.compras.guardar(compra)
            raise PagoInformeError(
                e.mensaje, codigo=e.codigo, buy_order=buy_order
            ) from e
        except Exception as e:
            compra.estado = ESTADO_ERROR
            compra.error_codigo = "tbk_create_ex"
            compra.error_detalle = str(e)[:500]
            self.compras.guardar(compra)
            raise PagoInformeError(
                "Error inesperado al iniciar el pago.",
                codigo="tbk_create_ex",
                buy_order=buy_order,
            ) from e
        compra.token = tx.token
        compra.estado = ESTADO_PENDIENTE
        self.compras.guardar(compra)
        return InicioPagoInforme(
            buy_order=buy_order,
            token=tx.token,
            url=tx.url,
            monto=self.monto,
            business_id=business_id,
            reclamo=self.reclamo_para(buy_order),
        )

    def confirmar(self, usuario: Usuario, token: str) -> ConfirmacionPagoInforme:
        token = (token or "").strip()
        if len(token) < 8:
            raise PagoInformeError(
                "Token de pago inválido o ausente.", codigo="token_invalido"
            )
        marca, compra = self.compras.reclamar_para_confirmar(token, usuario.id)
        if marca == "no" or compra is None:
            raise PagoInformeError(
                "No encontramos esta compra. Use la orden para reclamar.",
                codigo="compra_no_encontrada",
            )
        if marca == "ajena":
            raise PagoInformeError(
                "Esta compra pertenece a otra cuenta.",
                codigo="compra_ajena",
                buy_order=compra.buy_order,
            )
        if marca == "ya_ok":
            return self._respuesta(compra, usuario, ya_ok=True)
        if marca == "en_curso":
            raise PagoInformeError(
                "La confirmación ya está en curso. Espere unos segundos.",
                codigo="confirmacion_en_curso",
                buy_order=compra.buy_order,
            )
        if marca == "estado":
            raise PagoInformeError(
                "Esta compra no se puede confirmar en su estado actual.",
                codigo="estado_invalido",
                buy_order=compra.buy_order,
            )
        compra = self._aplicar_commit_tbk(compra, token)
        return self._respuesta(compra, usuario, ya_ok=False)

    def _restaurar_pendiente(self, compra) -> None:
        compra.estado = ESTADO_PENDIENTE
        compra.error_codigo = None
        compra.error_detalle = None
        self.compras.guardar(compra)

    def _aplicar_commit_tbk(
        self, compra, token: str, *, reintentable: bool = False
    ):
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
            raise PagoInformeError(
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
            raise PagoInformeError(
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

    def _entregar_tras_autorizar(self, compra) -> None:

        if compra.estado != ESTADO_AUTORIZADO or self.usuarios is None:
            return
        usuario = self.usuarios.obtener(compra.usuario_id)
        if usuario is None:
            return
        try:
            self._respuesta(compra, usuario, ya_ok=False)
        except Exception:

            pass

    def reconciliar_pendientes(
        self,
        *,
        min_edad_seg: int = 180,
        max_edad_seg: int = 7200,
        limite: int = 25,
    ) -> int:

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
                    self._entregar_tras_autorizar(actualizada)
                    cerrados += 1
                elif actualizada.estado == ESTADO_RECHAZADO:
                    cerrados += 1
            except PagoInformeError:
                continue
            except Exception:
                try:
                    self._restaurar_pendiente(reclamada)
                except Exception:
                    pass
                continue
        return cerrados

    def marcar_anulado(
        self, usuario: Usuario, buy_order: str, motivo: str
    ) -> ConfirmacionPagoInforme:
        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoInformeError(
                "Compra no encontrada para anular.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        if compra.estado == ESTADO_AUTORIZADO:
            return self._respuesta(compra, usuario, ya_ok=True)
        compra.estado = ESTADO_ANULADO
        compra.error_codigo = "tbk_anulado"
        compra.error_detalle = (motivo or "Usuario canceló en Webpay")[:500]
        self.compras.guardar(compra)
        return self._respuesta(compra, usuario, ya_ok=False)

    def consultar(self, usuario: Usuario, buy_order: str) -> ConfirmacionPagoInforme:
        compra = self.compras.obtener_por_buy_order((buy_order or "").strip())
        if compra is None or compra.usuario_id != usuario.id:
            raise PagoInformeError(
                "Compra no encontrada.",
                codigo="compra_no_encontrada",
                buy_order=buy_order,
            )
        return self._respuesta(
            compra, usuario, ya_ok=compra.estado == ESTADO_AUTORIZADO
        )

    def _respuesta(
        self, compra, usuario: Usuario, *, ya_ok: bool
    ) -> ConfirmacionPagoInforme:
        enviado = False
        destino = None
        qr_payload = None
        expires_at = None
        if compra.estado == ESTADO_AUTORIZADO:
            try:
                informe = self.radar.informe(usuario, compra.business_id)
                enviado = informe.enviado
                destino = informe.destino
                qr_payload = informe.qr_payload
                expires_at = informe.qr_expira
            except Exception as e:
                compra.error_codigo = compra.error_codigo or "entrega_informe"
                compra.error_detalle = (
                    compra.error_detalle
                    or f"Pago autorizado; fallo al preparar informe: {e}"
                )[:500]
                self.compras.guardar(compra)
        print_token = None
        if compra.estado == ESTADO_AUTORIZADO:
            print_token = self.emitir_print_token(usuario, compra)
        return ConfirmacionPagoInforme(
            buy_order=compra.buy_order,
            estado=compra.estado,
            autorizado=compra.estado == ESTADO_AUTORIZADO,
            business_id=compra.business_id,
            monto=compra.monto,
            response_code=compra.response_code,
            authorization_code=compra.authorization_code,
            error_codigo=compra.error_codigo,
            error_detalle=compra.error_detalle,
            reclamo=self.reclamo_para(compra.buy_order),
            enviado=enviado,
            destino=destino,
            qr_payload=qr_payload,
            expires_at=expires_at,
            print_token=print_token,
        )
