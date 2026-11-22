from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.dependencias import (
    ServicioAutenticacionDep,
    ServicioCuentaDep,
    UsuarioActualDep,
    ServicioReporteIdentidadDep,
    LimiteSolicitudesDep,
    ConfiguracionDep,
    demasiadas_solicitudes,
)

from app.api.mapeos import to_usuario_out

from app.api.esquemas import EliminarCuentaEntrada, LoginEntrada, RegistroEntrada, TokenSalida, UsuarioSalida

from app.dominio.errores import (
    ContrasenaIncorrecta,
    CredencialesInvalidas,
    EmailYaRegistrado,
)

router = APIRouter(prefix="/v1/auth", tags=["Autenticación"])

CREDENCIALES_INCORRECTAS = "Correo o contraseña incorrectos."

def _ip(request: Request, settings) -> str:

    if settings.trust_proxy:

        xff = request.headers.get("x-forwarded-for")

        if xff:

            return xff.split(",")[-1].strip()

    return request.client.host if request.client else "desconocida"

def _limitar_intento(
    request: Request, accion: str, email: str, limiter, settings
) -> None:

    if not limiter.permitir(f"{accion}-correo:{email}", settings.login_rate_per_minute):

        raise demasiadas_solicitudes()

    if not limiter.permitir(
        f"{accion}-ip:{_ip(request, settings)}", settings.login_ip_rate_per_minute
    ):

        raise demasiadas_solicitudes()

@router.post(
    "/registro", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED
)
def registro(
    datos: RegistroEntrada,
    request: Request,
    auth: ServicioAutenticacionDep,
    identidad: ServicioReporteIdentidadDep,
    limiter: LimiteSolicitudesDep,
    settings: ConfiguracionDep,
):

    _limitar_intento(request, "registro", datos.email.lower(), limiter, settings)

    perfil = datos.perfil.model_dump(exclude_unset=True)

    try:

        usuario = auth.registrar(datos.email, datos.nombre, datos.password, perfil)

    except EmailYaRegistrado:

        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este correo ya está registrado. Inicie sesión."
        ) from None

    return to_usuario_out(usuario, identidad.estado(usuario))

@router.post("/login", response_model=TokenSalida)
def login(
    datos: LoginEntrada,
    request: Request,
    auth: ServicioAutenticacionDep,
    limiter: LimiteSolicitudesDep,
    settings: ConfiguracionDep,
):

    _limitar_intento(request, "login", datos.email.lower(), limiter, settings)

    try:

        token = auth.login(datos.email, datos.password)

    except CredencialesInvalidas:

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, CREDENCIALES_INCORRECTAS
        ) from None

    return TokenSalida(access_token=token.access_token, expires_in=token.expires_in)

@router.get("/yo", response_model=UsuarioSalida)
def yo(usuario: UsuarioActualDep, identidad: ServicioReporteIdentidadDep):

    return to_usuario_out(usuario, identidad.estado(usuario))

@router.delete("/yo", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    datos: EliminarCuentaEntrada, usuario: UsuarioActualDep, cuenta: ServicioCuentaDep
):

    try:

        cuenta.eliminar(usuario, datos.password)

    except ContrasenaIncorrecta:

        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La contraseña no coincide."
        ) from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)
