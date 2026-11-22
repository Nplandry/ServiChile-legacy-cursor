from app.dominio.entidades import Usuario
from app.dominio.errores import ContrasenaIncorrecta
from app.dominio.puertos import (
    AlmacenamientoBiometria,
    AlmacenamientoCedula,
    HasheadorContrasena,
    RepositorioUsuarios,
)
from app.servicios.negocio import ServicioNegocio

__all__ = ["ServicioCuenta", "ContrasenaIncorrecta"]

class ServicioCuenta:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        negocios: ServicioNegocio,
        hasheador: HasheadorContrasena,
        biometria: AlmacenamientoBiometria | None = None,
        cedula: AlmacenamientoCedula | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.negocios = negocios
        self.hasheador = hasheador
        self.biometria = biometria
        self.cedula = cedula

    def eliminar(self, usuario: Usuario, contrasena: str) -> None:
        if not self.hasheador.verificar(usuario.password_hash, contrasena):
            raise ContrasenaIncorrecta()
        if self.biometria is not None:
            self.biometria.eliminar(usuario.id, usuario.biometria_ruta)
        if self.cedula is not None:
            self.cedula.eliminar(usuario.id, usuario.cedula_ruta)
        self.negocios.eliminar_todos_del_usuario(usuario.id)
        self.usuarios.eliminar(usuario.id)
