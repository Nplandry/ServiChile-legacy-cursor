

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.autorizacion import exige_cuenta_proveedor
from app.api.dependencias import (
    LimiteSolicitudesDep,
    ServicioPagoInformeDep,
    ServicioPagoPublicacionDep,
    UsuarioActualDep,
    demasiadas_solicitudes,
)
from app.api.esquemas.pagos import (
    AnularPagoInformeEntrada,
    AnularPagoPublicacionEntrada,
    CanalReclamoSalida,
    CatalogoPagoInformeSalida,
    CatalogoPagoPublicacionSalida,
    ConfirmacionPagoInformeSalida,
    ConfirmacionPagoPublicacionSalida,
    ConfirmarPagoInformeEntrada,
    ConfirmarPagoPublicacionEntrada,
    IniciarPagoInformeEntrada,
    IniciarPagoPublicacionEntrada,
    InicioPagoInformeSalida,
    InicioPagoPublicacionSalida,
    RecuperarPagoInformeEntrada,
    RecuperarPagoPublicacionEntrada,
    ResumenComprasInformeSalida,
    VerificarPrintEntrada,
)
from uuid import UUID

from app.dominio.errores import (
    InformeSinCompra,
    NegocioNoEncontrado,
    PagoInformeError,
    PagoPublicacionError,
)
from app.dominio.pago_informe import CanalReclamo, ConfirmacionPagoInforme, InicioPagoInforme
from app.dominio.pago_publicacion import (
    CanalReclamoPublicacion,
    ConfirmacionPagoPublicacion,
    InicioPagoPublicacion,
)
from app.servicios.pago_informe import ServicioPagoInforme
from app.servicios.pago_publicacion import ServicioPagoPublicacion

router = APIRouter(prefix="/v1/pagos", tags=["Pagos"])

def _reclamo(c: CanalReclamo) -> CanalReclamoSalida:
    return CanalReclamoSalida(
        email=c.email, whatsapp=c.whatsapp, instruccion=c.instruccion
    )

def _inicio(out: InicioPagoInforme) -> InicioPagoInformeSalida:
    return InicioPagoInformeSalida(
        buy_order=out.buy_order,
        token=out.token,
        url=out.url,
        monto=out.monto,
        business_id=out.business_id,
        reclamo=_reclamo(out.reclamo),
    )

def _confirmacion(out: ConfirmacionPagoInforme) -> ConfirmacionPagoInformeSalida:
    return ConfirmacionPagoInformeSalida(
        buy_order=out.buy_order,
        estado=out.estado,
        autorizado=out.autorizado,
        business_id=out.business_id,
        monto=out.monto,
        response_code=out.response_code,
        authorization_code=out.authorization_code,
        error_codigo=out.error_codigo,
        error_detalle=out.error_detalle,
        reclamo=_reclamo(out.reclamo),
        enviado=out.enviado,
        destino=out.destino,
        qr_payload=out.qr_payload,
        expires_at=out.expires_at,
        print_token=out.print_token,
    )

def _http_pago(
    e: PagoInformeError, servicio: ServicioPagoInforme | None = None
) -> HTTPException:
    detalle = {
        "mensaje": e.mensaje,
        "codigo": e.codigo,
        "buy_order": e.buy_order,
    }
    if servicio is not None and e.buy_order:
        detalle["reclamo"] = _reclamo(servicio.reclamo_para(e.buy_order)).model_dump()
    codigo_http = status.HTTP_400_BAD_REQUEST
    if e.codigo == "confirmacion_en_curso":
        codigo_http = status.HTTP_409_CONFLICT
    elif e.codigo == "ya_comprado":
        codigo_http = status.HTTP_409_CONFLICT
    return HTTPException(codigo_http, detalle)

@router.get("/informe/catalogo", response_model=CatalogoPagoInformeSalida)
def catalogo_pago_informe(servicio: ServicioPagoInformeDep):
    cat = servicio.catalogo()
    return CatalogoPagoInformeSalida(
        monto=cat.monto, moneda=cat.moneda, producto=cat.producto
    )

@router.get("/informe/resumen", response_model=ResumenComprasInformeSalida)
def resumen_compras_informe(
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
):
    r = servicio.resumen_usuario(usuario)
    return ResumenComprasInformeSalida(
        autorizadas_mes=r.autorizadas_mes,
        gastado_mes=r.gastado_mes,
        monto_unitario=r.monto_unitario,
    )

@router.get(
    "/informe/acceso/{business_id}",
    response_model=ConfirmacionPagoInformeSalida,
)
def acceso_informe_comprado(
    business_id: UUID,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):

    if not limiter.permitir(f"pago-acceso:{usuario.id}", 20):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(servicio.reentregar(usuario, business_id))
    except NegocioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Negocio no encontrado."
        ) from None
    except InformeSinCompra as e:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {"mensaje": e.mensaje, "codigo": e.codigo, "autorizado": False},
        ) from None

@router.post("/informe", response_model=InicioPagoInformeSalida)
def iniciar_pago_informe(
    datos: IniciarPagoInformeEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-ini:{usuario.id}", 8):
        raise demasiadas_solicitudes()
    try:
        retorno = servicio.validar_return_url(datos.return_url)
        return _inicio(servicio.iniciar(usuario, datos.business_id, retorno))
    except NegocioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Negocio no encontrado."
        ) from None
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

@router.post("/informe/recuperar", response_model=ConfirmacionPagoInformeSalida)
def recuperar_pago_informe(
    datos: RecuperarPagoInformeEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-rec:{usuario.id}", 8):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(servicio.recuperar(usuario, datos.buy_order))
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

@router.post("/informe/verificar-print", response_model=ConfirmacionPagoInformeSalida)
def verificar_print_informe(
    datos: VerificarPrintEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-print:{usuario.id}", 30):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(
            servicio.verificar_print_token(
                usuario, datos.business_id, datos.print_token
            )
        )
    except InformeSinCompra as e:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {"mensaje": e.mensaje, "codigo": e.codigo},
        ) from None
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

@router.post("/informe/confirmar", response_model=ConfirmacionPagoInformeSalida)
def confirmar_pago_informe(
    datos: ConfirmarPagoInformeEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-ok:{usuario.id}", 12):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(servicio.confirmar(usuario, datos.token))
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

@router.post("/informe/anular", response_model=ConfirmacionPagoInformeSalida)
def anular_pago_informe(
    datos: AnularPagoInformeEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-anular:{usuario.id}", 12):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(
            servicio.marcar_anulado(
                usuario, datos.buy_order, datos.motivo or "Cancelado en Webpay"
            )
        )
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

@router.get("/informe/{buy_order}", response_model=ConfirmacionPagoInformeSalida)
def estado_pago_informe(
    buy_order: str,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoInformeDep,
    limiter: LimiteSolicitudesDep,
):
    if not limiter.permitir(f"pago-est:{usuario.id}", 20):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion(servicio.consultar(usuario, buy_order))
    except PagoInformeError as e:
        raise _http_pago(e, servicio) from None

def _reclamo_pub(c: CanalReclamoPublicacion) -> CanalReclamoSalida:
    return CanalReclamoSalida(
        email=c.email, whatsapp=c.whatsapp, instruccion=c.instruccion
    )

def _inicio_pub(out: InicioPagoPublicacion) -> InicioPagoPublicacionSalida:
    return InicioPagoPublicacionSalida(
        buy_order=out.buy_order,
        token=out.token,
        url=out.url,
        monto=out.monto,
        reclamo=_reclamo_pub(out.reclamo),
    )

def _confirmacion_pub(
    out: ConfirmacionPagoPublicacion,
) -> ConfirmacionPagoPublicacionSalida:
    return ConfirmacionPagoPublicacionSalida(
        buy_order=out.buy_order,
        estado=out.estado,
        autorizado=out.autorizado,
        monto=out.monto,
        response_code=out.response_code,
        authorization_code=out.authorization_code,
        error_codigo=out.error_codigo,
        error_detalle=out.error_detalle,
        reclamo=_reclamo_pub(out.reclamo),
        business_id=out.business_id,
        consumido=out.consumido,
    )

def _http_pago_pub(
    e: PagoPublicacionError, servicio: ServicioPagoPublicacion | None = None
) -> HTTPException:
    detalle = {
        "mensaje": e.mensaje,
        "codigo": e.codigo,
        "buy_order": e.buy_order,
    }
    if servicio is not None and e.buy_order:
        detalle["reclamo"] = _reclamo_pub(
            servicio.reclamo_para(e.buy_order)
        ).model_dump()
    codigo_http = status.HTTP_400_BAD_REQUEST
    if e.codigo == "confirmacion_en_curso":
        codigo_http = status.HTTP_409_CONFLICT
    elif e.codigo == "cupon_disponible":
        codigo_http = status.HTTP_409_CONFLICT
    return HTTPException(codigo_http, detalle)

@router.get("/publicacion/catalogo", response_model=CatalogoPagoPublicacionSalida)
def catalogo_pago_publicacion(servicio: ServicioPagoPublicacionDep):
    cat = servicio.catalogo()
    return CatalogoPagoPublicacionSalida(
        monto=cat.monto, moneda=cat.moneda, producto=cat.producto
    )

@router.get("/publicacion/acceso", response_model=ConfirmacionPagoPublicacionSalida)
def acceso_cupon_publicacion(
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-acc:{usuario.id}", 20):
        raise demasiadas_solicitudes()
    cupon = servicio.cupon_disponible(usuario)
    if cupon is None:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            {
                "mensaje": "No hay un pago de publicación listo.",
                "codigo": "publicacion_sin_pago",
                "autorizado": False,
            },
        )
    return _confirmacion_pub(cupon)

@router.post("/publicacion", response_model=InicioPagoPublicacionSalida)
def iniciar_pago_publicacion(
    datos: IniciarPagoPublicacionEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-ini:{usuario.id}", 8):
        raise demasiadas_solicitudes()
    try:
        retorno = servicio.validar_return_url(datos.return_url)
        return _inicio_pub(servicio.iniciar(usuario, retorno))
    except PagoPublicacionError as e:
        raise _http_pago_pub(e, servicio) from None

@router.post(
    "/publicacion/confirmar", response_model=ConfirmacionPagoPublicacionSalida
)
def confirmar_pago_publicacion(
    datos: ConfirmarPagoPublicacionEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-ok:{usuario.id}", 12):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion_pub(servicio.confirmar(usuario, datos.token))
    except PagoPublicacionError as e:
        raise _http_pago_pub(e, servicio) from None

@router.post(
    "/publicacion/recuperar", response_model=ConfirmacionPagoPublicacionSalida
)
def recuperar_pago_publicacion(
    datos: RecuperarPagoPublicacionEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-rec:{usuario.id}", 8):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion_pub(servicio.recuperar(usuario, datos.buy_order))
    except PagoPublicacionError as e:
        raise _http_pago_pub(e, servicio) from None

@router.post(
    "/publicacion/anular", response_model=ConfirmacionPagoPublicacionSalida
)
def anular_pago_publicacion(
    datos: AnularPagoPublicacionEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-an:{usuario.id}", 12):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion_pub(
            servicio.marcar_anulado(
                usuario, datos.buy_order, datos.motivo or "Cancelado en Webpay"
            )
        )
    except PagoPublicacionError as e:
        raise _http_pago_pub(e, servicio) from None

@router.get(
    "/publicacion/{buy_order}", response_model=ConfirmacionPagoPublicacionSalida
)
def estado_pago_publicacion(
    buy_order: str,
    usuario: UsuarioActualDep,
    servicio: ServicioPagoPublicacionDep,
    limiter: LimiteSolicitudesDep,
):
    exige_cuenta_proveedor(usuario)
    if not limiter.permitir(f"pago-pub-est:{usuario.id}", 20):
        raise demasiadas_solicitudes()
    try:
        return _confirmacion_pub(servicio.consultar(usuario, buy_order))
    except PagoPublicacionError as e:
        raise _http_pago_pub(e, servicio) from None
