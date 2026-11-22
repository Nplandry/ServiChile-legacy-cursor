

from functools import lru_cache

from typing import Annotated

from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.orm import Session

from app.configuracion import Configuracion, obtener_configuracion
from app.infraestructura.cache_respuesta import CacheRespuesta

from app.dominio.entidades import Usuario

from app.dominio.errores import CredencialesInvalidas

from app.dominio.puertos import (
    AlmacenamientoBiometria,
    AlmacenamientoCedula,
    AnalizadorAntecedentes,
    AnalizadorAval,
    AnalizadorCedula,
    AnalizadorDocEmpresa,
    EnviadorPlataforma,
    EmisorReporte,
    EmisorSesion,
    HasheadorContrasena,
    VerificadorIdentidad,
)

from app.infraestructura.biometria_fs import AlmacenamientoBiometriaLocal

from app.infraestructura.cedula_fs import AlmacenamientoCedulaLocal

from app.infraestructura.cedula_ocr import AnalizadorCedulaOcr, LectorOcrTesseract
from app.infraestructura.cedula_vision import ComparadorRostrosOpenCv

from app.infraestructura.pdf_antecedentes import AnalizadorPdfAntecedentes
from app.infraestructura.pdf_aval import AnalizadorPdfAval
from app.infraestructura.pdf_docs_empresa import AnalizadorPdfDocEmpresa

from app.infraestructura.persistencia.modelos import obtener_sesion

from app.infraestructura.limite_solicitudes import (
    LimiteSolicitudes,
    construir_limite_solicitudes,
)

from app.infraestructura.correo_plataforma import EnviadorMemoria, EnviadorSmtp
from app.infraestructura.persistencia.repositorios import (
    RepositorioCompraInforme,
    RepositorioCompraPublicacion,
    RepositorioCorreo,
    RepositorioNegocio,
    RepositorioTrabajo,
    RepositorioUsuario,
    RepositorioXp,
)

from app.infraestructura.seguridad.hasheador import HasheadorArgon2

from app.infraestructura.seguridad.jwt_reporte import JwtReporte

from app.infraestructura.seguridad.jwt_sesion import JwtSesion

from app.infraestructura.verificacion import construir_verificador_rut

from app.ensamblado.evaluador import armar_servicio_negocio

from app.servicios.autenticacion import ServicioAutenticacion

from app.servicios.cuenta import ServicioCuenta

from app.servicios.negocio import ServicioNegocio

from app.servicios.radar_comercial import ServicioRadarComercial
from app.servicios.pago_informe import ServicioPagoInforme
from app.servicios.pago_publicacion import ServicioPagoPublicacion
from app.servicios.reporte_identidad import ServicioReporteIdentidad

from app.servicios.reporte import ServicioReporte

from app.servicios.trabajo import ServicioTrabajo

from app.servicios.progreso_cliente import ServicioProgresoCliente
from app.ensamblado.pagos import (
    obtener_pasarela_webpay,
    permitir_pasarela_memoria,
)

SesionDep = Annotated[Session, Depends(obtener_sesion)]

ConfiguracionDep = Annotated[Configuracion, Depends(obtener_configuracion)]

@lru_cache
def obtener_limite_solicitudes() -> LimiteSolicitudes:

    return construir_limite_solicitudes(obtener_configuracion().redis_url)

@lru_cache
def obtener_cache_respuesta():
    from app.infraestructura.cache_respuesta import construir_cache_respuesta

    cfg = obtener_configuracion()
    return construir_cache_respuesta(
        cfg.redis_url, activo=cfg.app_env != "test"
    )

def obtener_servicio_progreso(session: SesionDep) -> ServicioProgresoCliente:

    return ServicioProgresoCliente(RepositorioXp(session))

@lru_cache
def obtener_hasheador() -> HasheadorContrasena:

    return HasheadorArgon2()

@lru_cache
def obtener_emisor_sesion() -> EmisorSesion:

    settings = obtener_configuracion()

    return JwtSesion(
        settings.jwt_secret.get_secret_value(), settings.jwt_expires_minutes
    )

@lru_cache
def obtener_emisor_reporte() -> EmisorReporte:

    settings = obtener_configuracion()

    return JwtReporte(
        settings.jwt_secret.get_secret_value(), settings.reporte_expires_minutes
    )

def obtener_servicio_autenticacion(
    session: SesionDep,
    hasheador: Annotated[HasheadorContrasena, Depends(obtener_hasheador)],
    sesion: Annotated[EmisorSesion, Depends(obtener_emisor_sesion)],
) -> ServicioAutenticacion:

    return ServicioAutenticacion(
        RepositorioUsuario(session),
        hasheador,
        sesion,
        obtener_servicio_progreso(session),
    )

def obtener_verificador_rut() -> VerificadorIdentidad:
    s = obtener_configuracion()
    return construir_verificador_rut(
        s.rut_verifier,
        app_env=s.app_env,
        chilecompra_ticket=getattr(s, "chilecompra_ticket", "") or "",
    )

@lru_cache
def obtener_analizador_antecedentes() -> AnalizadorAntecedentes:
    settings = obtener_configuracion()
    return AnalizadorPdfAntecedentes(str(settings.pades_ca_ruta()))

@lru_cache
def obtener_almacenamiento_biometria() -> AlmacenamientoBiometria:
    settings = obtener_configuracion()
    return AlmacenamientoBiometriaLocal(
        settings.biometria_raiz(),
        max_lado=settings.biometria_max_lado,
        calidad_jpeg=settings.biometria_jpeg_quality,
    )

@lru_cache
def obtener_almacenamiento_cedula() -> AlmacenamientoCedula:
    settings = obtener_configuracion()
    return AlmacenamientoCedulaLocal(
        settings.cedula_raiz(),
        max_lado=settings.cedula_max_lado,
        calidad_jpeg=settings.cedula_jpeg_quality,
    )

@lru_cache
def obtener_analizador_cedula() -> AnalizadorCedula:
    return AnalizadorCedulaOcr(LectorOcrTesseract(), ComparadorRostrosOpenCv())

@lru_cache
def obtener_analizador_aval() -> AnalizadorAval:
    return AnalizadorPdfAval()

@lru_cache
def obtener_analizador_docs_empresa() -> AnalizadorDocEmpresa:
    settings = obtener_configuracion()
    return AnalizadorPdfDocEmpresa(str(settings.pades_ca_ruta()))

def obtener_servicio_reporte_identidad(
    session: SesionDep,
    verificador: Annotated[VerificadorIdentidad, Depends(obtener_verificador_rut)],
    analizador: Annotated[AnalizadorAntecedentes, Depends(obtener_analizador_antecedentes)],
    biometria: Annotated[
        AlmacenamientoBiometria, Depends(obtener_almacenamiento_biometria)
    ],
    cedula: Annotated[AlmacenamientoCedula, Depends(obtener_almacenamiento_cedula)],
    analizador_cedula: Annotated[AnalizadorCedula, Depends(obtener_analizador_cedula)],
    analizador_aval: Annotated[AnalizadorAval, Depends(obtener_analizador_aval)],
    settings: ConfiguracionDep,
) -> ServicioReporteIdentidad:

    return ServicioReporteIdentidad(
        RepositorioUsuario(session),
        RepositorioTrabajo(session),
        verificador,
        obtener_servicio_progreso(session),
        analizador,
        biometria,
        biometria_retencion_dias=settings.biometria_retencion_dias,
        cedula=cedula,
        analizador_cedula=analizador_cedula,
        cedula_retencion_dias=settings.cedula_retencion_dias,
        analizador_aval=analizador_aval,
    )

def obtener_servicio_negocio(
    session: SesionDep,
    analizador_docs: Annotated[
        AnalizadorDocEmpresa, Depends(obtener_analizador_docs_empresa)
    ],
) -> ServicioNegocio:
    return armar_servicio_negocio(session, analizador_docs)

@lru_cache
def obtener_enviador() -> EnviadorPlataforma:
    settings = obtener_configuracion()
    if settings.app_env == "test":
        return EnviadorMemoria(simular=True)
    if not settings.smtp_host.strip() or not settings.smtp_desde.strip():
        return EnviadorMemoria(simular=False)
    return EnviadorSmtp(
        settings.smtp_host.strip(),
        settings.smtp_port,
        settings.smtp_usuario.strip(),
        settings.smtp_clave.get_secret_value(),
        settings.smtp_desde.strip(),
        starttls=settings.smtp_starttls,
    )

def obtener_servicio_radar(
    session: SesionDep,
    enviador: Annotated[EnviadorPlataforma, Depends(obtener_enviador)],
    emisor: Annotated[EmisorReporte, Depends(obtener_emisor_reporte)],
) -> ServicioRadarComercial:
    return ServicioRadarComercial(
        RepositorioNegocio(session),
        RepositorioUsuario(session),
        RepositorioCorreo(session),
        enviador,
        emisor,
    )

def obtener_servicio_pago_informe(
    session: SesionDep,
    radar: Annotated[ServicioRadarComercial, Depends(obtener_servicio_radar)],
) -> ServicioPagoInforme:
    settings = obtener_configuracion()
    retorno = (settings.public_frontend_url or "").strip()
    if "pago=retorno" not in retorno:
        sep = "&" if "?" in retorno else "?"
        retorno = f"{retorno}{sep}pago=retorno"
    from app.dominio.pago_informe import PRECIO_INFORME_CLP

    return ServicioPagoInforme(
        RepositorioCompraInforme(session),
        RepositorioNegocio(session),
        obtener_pasarela_webpay(),
        radar,
        return_url=retorno,
        reclamo_email=settings.pagos_reclamo_email,
        reclamo_whatsapp=settings.pagos_reclamo_whatsapp,
        monto=PRECIO_INFORME_CLP,
        origenes_permitidos=list(settings.cors_origins or []),
        print_secret=settings.secreto_print_token(),
        usuarios=RepositorioUsuario(session),
    )

def obtener_servicio_pago_publicacion(
    session: SesionDep,
    enviador: Annotated[EnviadorPlataforma, Depends(obtener_enviador)],
) -> ServicioPagoPublicacion:
    settings = obtener_configuracion()
    retorno = (settings.public_frontend_url or "").strip()
    if "pago=retorno" not in retorno:
        sep = "&" if "?" in retorno else "?"
        retorno = f"{retorno}{sep}pago=retorno"
    if "producto=publicacion" not in retorno:
        retorno = f"{retorno}&producto=publicacion"
    from app.dominio.pago_publicacion import PRECIO_PUBLICACION_CLP

    return ServicioPagoPublicacion(
        RepositorioCompraPublicacion(session),
        obtener_pasarela_webpay(),
        return_url=retorno,
        reclamo_email=settings.pagos_reclamo_email,
        reclamo_whatsapp=settings.pagos_reclamo_whatsapp,
        monto=PRECIO_PUBLICACION_CLP,
        origenes_permitidos=list(settings.cors_origins or []),
        usuarios=RepositorioUsuario(session),
        enviador=enviador,
    )

def obtener_servicio_trabajo(session: SesionDep) -> ServicioTrabajo:

    return ServicioTrabajo(
        RepositorioNegocio(session),
        RepositorioTrabajo(session),
        obtener_servicio_progreso(session),
    )

def obtener_servicio_reporte(
    session: SesionDep,
    identidad: Annotated[
        ServicioReporteIdentidad, Depends(obtener_servicio_reporte_identidad)
    ],
    emisor: Annotated[EmisorReporte, Depends(obtener_emisor_reporte)],
) -> ServicioReporte:

    return ServicioReporte(RepositorioUsuario(session), identidad, emisor)

def obtener_servicio_cuenta(
    session: SesionDep,
    negocios: Annotated[ServicioNegocio, Depends(obtener_servicio_negocio)],
    hasheador: Annotated[HasheadorContrasena, Depends(obtener_hasheador)],
    biometria: Annotated[
        AlmacenamientoBiometria, Depends(obtener_almacenamiento_biometria)
    ],
    cedula: Annotated[AlmacenamientoCedula, Depends(obtener_almacenamiento_cedula)],
) -> ServicioCuenta:

    return ServicioCuenta(
        RepositorioUsuario(session), negocios, hasheador, biometria, cedula
    )

ServicioReporteIdentidadDep = Annotated[
    ServicioReporteIdentidad, Depends(obtener_servicio_reporte_identidad)
]

ServicioTrabajoDep = Annotated[ServicioTrabajo, Depends(obtener_servicio_trabajo)]

ServicioReporteDep = Annotated[ServicioReporte, Depends(obtener_servicio_reporte)]

ServicioNegocioDep = Annotated[ServicioNegocio, Depends(obtener_servicio_negocio)]

ServicioRadarDep = Annotated[ServicioRadarComercial, Depends(obtener_servicio_radar)]

ServicioPagoInformeDep = Annotated[
    ServicioPagoInforme, Depends(obtener_servicio_pago_informe)
]

ServicioPagoPublicacionDep = Annotated[
    ServicioPagoPublicacion, Depends(obtener_servicio_pago_publicacion)
]

ServicioCuentaDep = Annotated[ServicioCuenta, Depends(obtener_servicio_cuenta)]

_bearer = HTTPBearer(auto_error=False)

def obtener_usuario_actual(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
) -> Usuario:

    if credentials is None:

        raise _no_autorizado()

    try:

        return auth.usuario_desde_token(credentials.credentials)

    except CredencialesInvalidas:

        raise _no_autorizado() from None

def obtener_usuario_opcional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
) -> Usuario | None:
    if credentials is None:
        return None
    try:
        return auth.usuario_desde_token(credentials.credentials)
    except CredencialesInvalidas:
        return None

def _no_autorizado() -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión inválida o expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

ServicioAutenticacionDep = Annotated[
    ServicioAutenticacion, Depends(obtener_servicio_autenticacion)
]

UsuarioActualDep = Annotated[Usuario, Depends(obtener_usuario_actual)]
UsuarioOpcionalDep = Annotated[Usuario | None, Depends(obtener_usuario_opcional)]

LimiteSolicitudesDep = Annotated[LimiteSolicitudes, Depends(obtener_limite_solicitudes)]

CacheRespuestaDep = Annotated[CacheRespuesta, Depends(obtener_cache_respuesta)]

def demasiadas_solicitudes() -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Demasiados intentos. Espere un minuto e intente de nuevo.",
        headers={"Retry-After": "60"},
    )
