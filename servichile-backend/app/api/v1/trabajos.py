import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.dependencias import (
    UsuarioActualDep,
    ServicioReporteIdentidadDep,
    ServicioTrabajoDep,
    CacheRespuestaDep,
)
from app.infraestructura.cache_respuesta import invalidar_negocio
from app.api.esquemas import ConcretarEntrada, TrabajoEntrada, TrabajoSalida
from app.dominio.errores import (
    NegocioNoEncontrado,
    NivelInsuficiente,
    NoEsTitularDelNegocio,
    TrabajoNoEncontrado,
    TrabajoYaCerrado,
)

router = APIRouter(prefix="/v1/trabajos", tags=["Trabajos"])

titular_router = APIRouter(
    prefix="/v1/businesses", tags=["Trabajos · titular"]
)

NO_ENCONTRADO = "Negocio no encontrado."
NO_TITULAR = "Solo el titular verificado del negocio puede registrar trabajos."
TRABAJO_NO_ENCONTRADO = "Trabajo no encontrado en este negocio."
TRABAJO_CERRADO = "El trabajo ya está cerrado (concretado, no concretado o cancelado)."

def _http_titular_trabajo(exc: Exception) -> HTTPException:
    if isinstance(exc, NegocioNoEncontrado):
        return HTTPException(status.HTTP_404_NOT_FOUND, NO_ENCONTRADO)
    if isinstance(exc, NoEsTitularDelNegocio):
        return HTTPException(status.HTTP_403_FORBIDDEN, NO_TITULAR)
    if isinstance(exc, TrabajoNoEncontrado):
        return HTTPException(status.HTTP_404_NOT_FOUND, TRABAJO_NO_ENCONTRADO)
    if isinstance(exc, TrabajoYaCerrado):
        return HTTPException(status.HTTP_409_CONFLICT, TRABAJO_CERRADO)
    raise exc

@router.post("", response_model=TrabajoSalida, status_code=status.HTTP_201_CREATED)
def crear_trabajo(
    datos: TrabajoEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioTrabajoDep,
    identidad: ServicioReporteIdentidadDep,
):
    nivel = identidad.estado(usuario).nivel_reporte
    try:
        return servicio.crear(usuario.id, datos.business_id, nivel)
    except NegocioNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Negocio no encontrado."
        ) from None
    except NivelInsuficiente as e:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Este proveedor pide nivel {e.requiere}. Suba su nivel de confianza para continuar.",
        ) from None

@router.get("", response_model=list[TrabajoSalida])
def listar_trabajos(usuario: UsuarioActualDep, servicio: ServicioTrabajoDep):
    return servicio.listar(usuario.id)

@router.delete("/{trabajo_id}", response_model=TrabajoSalida)
def cancelar_trabajo(
    trabajo_id: uuid.UUID, usuario: UsuarioActualDep, servicio: ServicioTrabajoDep
):
    try:
        return servicio.cancelar(usuario.id, trabajo_id)
    except TrabajoNoEncontrado:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Trabajo no encontrado."
        ) from None
    except TrabajoYaCerrado:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El trabajo ya no está abierto."
        ) from None

@titular_router.get("/{business_id}/trabajos", response_model=list[TrabajoSalida])
def listar_trabajos_negocio(
    business_id: uuid.UUID,
    usuario: UsuarioActualDep,
    servicio: ServicioTrabajoDep,
):
    try:
        return servicio.listar_del_negocio(business_id, usuario.id)
    except (NegocioNoEncontrado, NoEsTitularDelNegocio) as exc:
        raise _http_titular_trabajo(exc) from None

@titular_router.post("/{business_id}/trabajos/concretar", response_model=TrabajoSalida)
def registrar_concretado(
    business_id: uuid.UUID,
    datos: ConcretarEntrada,
    usuario: UsuarioActualDep,
    servicio: ServicioTrabajoDep,
    cache: CacheRespuestaDep,
):
    try:
        out = servicio.registrar_concretado(business_id, usuario.id, datos.qr_token)
    except (
        NegocioNoEncontrado,
        NoEsTitularDelNegocio,
        TrabajoNoEncontrado,
        TrabajoYaCerrado,
    ) as exc:
        raise _http_titular_trabajo(exc) from None
    invalidar_negocio(cache, business_id)
    return out

@titular_router.post(
    "/{business_id}/trabajos/{trabajo_id}/no-concretado", response_model=TrabajoSalida
)
def registrar_no_concretado(
    business_id: uuid.UUID,
    trabajo_id: uuid.UUID,
    usuario: UsuarioActualDep,
    servicio: ServicioTrabajoDep,
    cache: CacheRespuestaDep,
):
    try:
        out = servicio.registrar_no_concretado(business_id, usuario.id, trabajo_id)
    except (
        NegocioNoEncontrado,
        NoEsTitularDelNegocio,
        TrabajoNoEncontrado,
        TrabajoYaCerrado,
    ) as exc:
        raise _http_titular_trabajo(exc) from None
    invalidar_negocio(cache, business_id)
    return out
