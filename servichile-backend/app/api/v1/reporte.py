from fastapi import APIRouter, HTTPException, status

from app.api.dependencias import (
    UsuarioActualDep,
    LimiteSolicitudesDep,
    ServicioReporteDep,
    demasiadas_solicitudes,
)

from app.api.esquemas import ReporteSalida, ReporteValidacionSalida, ReporteValidarEntrada

from app.dominio.errores import ReporteInvalido

router = APIRouter(prefix="/v1/reporte", tags=["Reporte"])

VALIDAR_POR_MINUTO = 30

@router.get("", response_model=ReporteSalida)
def emitir_reporte(usuario: UsuarioActualDep, servicio: ServicioReporteDep):

    emitido = servicio.emitir(usuario)

    return ReporteSalida(
        payload=emitido.payload,
        token=emitido.token,
        expires_in=emitido.expires_in,
        expires_at=emitido.expires_at,
        nombre=emitido.nombre,
        email=emitido.email,
        nivel_reporte=emitido.nivel_reporte,
        estado_reporte=emitido.estado_reporte,
        score_confiabilidad=emitido.score_confiabilidad,
        rut_verificado=emitido.rut_verificado,
        xp=emitido.xp,
        nivel_xp=emitido.nivel_xp,
        tipo_cuenta=emitido.tipo_cuenta,
        antecedentes_verificados=emitido.antecedentes_verificados,
        antecedentes_anotaciones=emitido.antecedentes_anotaciones,
    )

@router.post("/validar", response_model=ReporteValidacionSalida)
def validar_reporte(
    datos: ReporteValidarEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioReporteDep,
    limiter: LimiteSolicitudesDep,
):

    if not limiter.permitir(f"reporte-validar:{usuario.id}", VALIDAR_POR_MINUTO):

        raise demasiadas_solicitudes()

    try:

        validado = servicio.validar(usuario, datos.payload)

    except ReporteInvalido as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    return ReporteValidacionSalida(
        es_propio=validado.es_propio,
        nombre=validado.nombre,
        nivel_reporte=validado.nivel_reporte,
        estado_reporte=validado.estado_reporte,
        score_confiabilidad=validado.score_confiabilidad,
        rut_verificado=validado.rut_verificado,
        expires_at=validado.expires_at,
        xp=validado.xp,
        nivel_xp=validado.nivel_xp,
        tipo_cuenta=validado.tipo_cuenta,
        antecedentes_verificados=validado.antecedentes_verificados,
        antecedentes_anotaciones=validado.antecedentes_anotaciones,
    )
