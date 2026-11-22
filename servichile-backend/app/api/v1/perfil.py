from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from starlette.concurrency import run_in_threadpool

from app.api.dependencias import (
    UsuarioActualDep,
    ServicioReporteIdentidadDep,
    LimiteSolicitudesDep,
    demasiadas_solicitudes,
)

from app.api.mapeos import to_perfil_out

from app.api.esquemas import (
    AntecedentesSalida,
    AvalSalida,
    BiometriaSalida,
    CedulaSalida,
    PerfilEntrada,
    PerfilSalida,
)

from app.dominio.antecedentes import ANTECEDENTES_MAX_BYTES
from app.dominio.aval import AVAL_MAX_BYTES

from app.dominio.errores import (
    AntecedentesInvalido,
    AntecedentesMuyGrande,
    AvalInvalido,
    AvalMuyGrande,
    BiometriaInvalida,
    BiometriaMuyGrande,
    CedulaInvalida,
    CedulaMuyGrande,
    RutEnUso,
    RutRechazado,
    RutYaVerificado,
)

from app.dominio.biometria import BIOMETRIA_MAX_BYTES

from app.dominio.cedula import CEDULA_MAX_BYTES

router = APIRouter(prefix="/v1/perfil", tags=["Perfil"])

BIOMETRIA_POR_MINUTO = 10

CEDULA_POR_MINUTO = 8

ANTECEDENTES_POR_MINUTO = 10

AVAL_POR_MINUTO = 8

@router.get("", response_model=PerfilSalida)
def ver_perfil(usuario: UsuarioActualDep, servicio: ServicioReporteIdentidadDep):

    return to_perfil_out(servicio.estado(usuario))

@router.patch("", response_model=PerfilSalida)
def actualizar_perfil(
    datos: PerfilEntrada, usuario: UsuarioActualDep, servicio: ServicioReporteIdentidadDep
):

    cambios = datos.model_dump(exclude_unset=True)

    try:

        actualizado = servicio.actualizar_perfil(usuario, cambios)

    except RutRechazado as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    except (RutEnUso, RutYaVerificado) as error:

        raise HTTPException(status.HTTP_409_CONFLICT, error.mensaje) from None

    return to_perfil_out(servicio.estado(actualizado))

@router.post(
    "/biometria", response_model=BiometriaSalida, status_code=status.HTTP_201_CREATED
)
async def verificar_biometria(
    usuario: UsuarioActualDep,
    servicio: ServicioReporteIdentidadDep,
    limiter: LimiteSolicitudesDep,
    foto: Annotated[
        UploadFile,
        File(
            description=(
                "Selfie de verificación; se guarda comprimida en disco local "
                "con retención limitada (no se expone públicamente)"
            )
        ),
    ],
):

    if not limiter.permitir(f"biometria:{usuario.id}", BIOMETRIA_POR_MINUTO):

        raise demasiadas_solicitudes()

    contenido = await foto.read(BIOMETRIA_MAX_BYTES + 1)

    try:

        actualizado = await run_in_threadpool(
            servicio.procesar_biometria, usuario, contenido
        )

    except BiometriaMuyGrande as error:

        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None

    except BiometriaInvalida as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    finally:

        del contenido

    estado = servicio.estado(actualizado)

    return BiometriaSalida(
        biometria_verificada=actualizado.biometria_verificada,
        biometria_verificada_en=actualizado.biometria_verificada_en,
        biometria_retener_hasta=actualizado.biometria_retener_hasta,
        biometria_bytes=actualizado.biometria_bytes,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
    )

@router.post(
    "/cedula", response_model=CedulaSalida, status_code=status.HTTP_201_CREATED
)
async def verificar_cedula(
    usuario: UsuarioActualDep,
    servicio: ServicioReporteIdentidadDep,
    limiter: LimiteSolicitudesDep,
    foto: Annotated[
        UploadFile,
        File(
            description="Foto frontal del carnet chileno; se valida con OCR (sin LLM)"
        ),
    ],
):
    if not limiter.permitir(f"cedula:{usuario.id}", CEDULA_POR_MINUTO):
        raise demasiadas_solicitudes()

    contenido = await foto.read(CEDULA_MAX_BYTES + 1)
    try:
        actualizado, resultado = await run_in_threadpool(
            servicio.procesar_cedula, usuario, contenido
        )
    except CedulaMuyGrande as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None
    except CedulaInvalida as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    except RutEnUso as error:
        raise HTTPException(status.HTTP_409_CONFLICT, error.mensaje) from None
    finally:
        del contenido

    estado = servicio.estado(actualizado)
    return CedulaSalida(
        cedula_verificada=actualizado.cedula_verificada,
        cedula_verificada_en=actualizado.cedula_verificada_en,
        cedula_retener_hasta=actualizado.cedula_retener_hasta,
        cedula_bytes=actualizado.cedula_bytes,
        cedula_score=actualizado.cedula_score,
        rut_verificado=actualizado.rut_verificado,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        senales=list(resultado.senales),
        face_score=resultado.face_score,
        motivo=resultado.motivo,
    )

@router.post(
    "/antecedentes", response_model=AntecedentesSalida, status_code=status.HTTP_201_CREATED
)
async def verificar_antecedentes(
    usuario: UsuarioActualDep,
    servicio: ServicioReporteIdentidadDep,
    limiter: LimiteSolicitudesDep,
    archivo: Annotated[
        UploadFile,
        File(description="PDF del certificado de antecedentes"),
    ],
    nombre_archivo: Annotated[str | None, Form()] = None,
):

    if not limiter.permitir(f"antecedentes:{usuario.id}", ANTECEDENTES_POR_MINUTO):

        raise demasiadas_solicitudes()

    contenido = await archivo.read(ANTECEDENTES_MAX_BYTES + 1)

    nombre = (nombre_archivo or archivo.filename or "").strip() or None

    try:

        actualizado, resultado = await run_in_threadpool(
            servicio.procesar_antecedentes, usuario, contenido, nombre
        )

    except AntecedentesMuyGrande as error:

        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None

    except AntecedentesInvalido as error:

        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None

    finally:

        del contenido

    estado = servicio.estado(actualizado)

    return AntecedentesSalida(
        antecedentes_verificados=actualizado.antecedentes_verificados,
        antecedentes_verificados_en=actualizado.antecedentes_verificados_en,
        antecedentes_anotaciones=actualizado.antecedentes_anotaciones,
        antecedentes_score=actualizado.antecedentes_score,
        verificado_criptograficamente=bool(resultado.verificado_criptograficamente),
        entidad_emisora=resultado.entidad_emisora,
        fecha_emision=resultado.fecha_emision,
        sha256_hash=resultado.sha256_hash,
        glosa=resultado.glosa,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        senales=list(resultado.senales),
        motivo=resultado.motivo,
    )

@router.post("/aval", response_model=AvalSalida, status_code=status.HTTP_201_CREATED)
async def verificar_aval(
    usuario: UsuarioActualDep,
    servicio: ServicioReporteIdentidadDep,
    limiter: LimiteSolicitudesDep,
    archivo: Annotated[
        UploadFile,
        File(
            description=(
                "PDF textual de aval o garantía de respaldo; no se admite escaneo "
                "ni foto"
            )
        ),
    ],
    nombre_archivo: Annotated[str | None, Form()] = None,
):
    if not limiter.permitir(f"aval:{usuario.id}", AVAL_POR_MINUTO):
        raise demasiadas_solicitudes()

    contenido = await archivo.read(AVAL_MAX_BYTES + 1)
    nombre = (nombre_archivo or archivo.filename or "").strip() or None
    try:
        actualizado, resultado = await run_in_threadpool(
            servicio.procesar_aval, usuario, contenido, nombre
        )
    except AvalMuyGrande as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, error.mensaje) from None
    except AvalInvalido as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, error.mensaje
        ) from None
    finally:
        del contenido

    estado = servicio.estado(actualizado)
    return AvalSalida(
        aval_verificado=actualizado.aval_verificado,
        aval_verificado_en=actualizado.aval_verificado_en,
        aval_score=actualizado.aval_score,
        aval_tipo=actualizado.aval_tipo,
        xp=estado.xp,
        nivel_xp=estado.nivel_xp,
        senales=list(resultado.senales),
        motivo=resultado.motivo,
    )
