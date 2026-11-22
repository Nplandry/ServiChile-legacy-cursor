import secrets
import uuid

from app.dominio.entidades import Trabajo
from app.dominio.errores import (
    NegocioNoEncontrado,
    NivelInsuficiente,
    NoEsTitularDelNegocio,
    TrabajoNoEncontrado,
    TrabajoYaCerrado,
)
from app.dominio.puertos import RepositorioNegocios, RepositorioTrabajos
from app.servicios.negocio_reputacion import persistir_indice
from app.servicios.progreso_cliente import ServicioProgresoCliente

__all__ = [
    "ServicioTrabajo",
    "TrabajoNoEncontrado",
    "TrabajoYaCerrado",
    "NoEsTitularDelNegocio",
    "NivelInsuficiente",
]

class ServicioTrabajo:

    def __init__(
        self,
        negocios: RepositorioNegocios,
        trabajos: RepositorioTrabajos,
        xp: ServicioProgresoCliente | None = None,
    ) -> None:
        self.negocios = negocios
        self.trabajos = trabajos
        self.xp = xp

    def crear(
        self, usuario_id: uuid.UUID, negocio_id: uuid.UUID, nivel_usuario: int = 1
    ) -> Trabajo:
        negocio = self.negocios.obtener(negocio_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        pide = negocio.requiere_nivel or 1
        if pide > nivel_usuario:
            raise NivelInsuficiente(pide)
        return self.trabajos.crear(usuario_id, negocio_id, secrets.token_urlsafe(24))

    def listar(self, usuario_id: uuid.UUID) -> list[Trabajo]:
        return self.trabajos.listar_por_usuario(usuario_id)

    def listar_del_negocio(
        self, negocio_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> list[Trabajo]:
        self._verificar_titular(negocio_id, usuario_id)
        return self.trabajos.listar_por_negocio(negocio_id)

    def cancelar(self, usuario_id: uuid.UUID, trabajo_id: uuid.UUID) -> Trabajo:
        trabajo = self.trabajos.obtener(trabajo_id)
        if trabajo is None or trabajo.usuario_id != usuario_id:
            raise TrabajoNoEncontrado()
        return self._cerrar(trabajo, "cancelado")

    def registrar_concretado(
        self, negocio_id: uuid.UUID, usuario_id: uuid.UUID, qr_token: str
    ) -> Trabajo:
        self._verificar_titular(negocio_id, usuario_id)
        trabajo = self.trabajos.obtener_por_qr(negocio_id, qr_token)
        if trabajo is None:
            raise TrabajoNoEncontrado()
        return self._cerrar(trabajo, "concretado")

    def registrar_no_concretado(
        self, negocio_id: uuid.UUID, usuario_id: uuid.UUID, trabajo_id: uuid.UUID
    ) -> Trabajo:
        self._verificar_titular(negocio_id, usuario_id)
        trabajo = self.trabajos.obtener(trabajo_id)
        if trabajo is None or trabajo.business_id != negocio_id:
            raise TrabajoNoEncontrado()
        return self._cerrar(trabajo, "no_concretado")

    def _verificar_titular(self, negocio_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
        negocio = self.negocios.obtener(negocio_id)
        if negocio is None:
            raise NegocioNoEncontrado()
        if not negocio.is_claimed or negocio.reclamado_por != usuario_id:
            raise NoEsTitularDelNegocio()

    def _cerrar(self, trabajo: Trabajo, estado: str) -> Trabajo:
        if trabajo.estado != "abierto":
            raise TrabajoYaCerrado()
        trabajo.estado = estado
        trabajo = self.trabajos.guardar(trabajo)
        if estado in ("concretado", "no_concretado"):
            self._refrescar_indice_negocio(trabajo.business_id)
        if estado == "concretado" and self.xp is not None:
            self.xp.por_trabajo_concretado(trabajo.usuario_id, trabajo.id)
        return trabajo

    def _refrescar_indice_negocio(self, negocio_id: uuid.UUID) -> None:
        negocio = self.negocios.obtener(negocio_id)
        if negocio is None:
            return
        conteo = self.trabajos.contar_concretados_por_negocios([negocio_id]).get(
            negocio_id, 0
        )
        persistir_indice(negocio, trabajos_concretados=conteo)
        self.negocios.guardar(negocio)
