from __future__ import annotations

import uuid

from app.dominio.entidades import TokenEmitido, Usuario
from app.dominio.errores import CredencialesInvalidas, EmailYaRegistrado
from app.dominio.puertos import EmisorSesion, HasheadorContrasena, RepositorioUsuarios
from app.servicios.perfil import aplicar_perfil
from app.servicios.progreso_cliente import ServicioProgresoCliente

class ServicioAutenticacion:
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        hasheador: HasheadorContrasena,
        sesion: EmisorSesion,
        xp: ServicioProgresoCliente | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.hasheador = hasheador
        self.sesion = sesion
        self.xp = xp

    def registrar(
        self, email: str, nombre: str, contrasena: str, perfil: dict | None
    ) -> Usuario:
        email = email.lower()
        if self.usuarios.obtener_por_email(email):
            raise EmailYaRegistrado()
        usuario = self.usuarios.crear(
            email, nombre, self.hasheador.hashear(contrasena)
        )
        if perfil:
            aplicar_perfil(usuario, perfil)
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            self.xp.por_registro(usuario.id)
            self.xp.por_perfil_basico(usuario)
            usuario.xp = self.xp.total(usuario.id)
        return usuario

    def login(self, email: str, contrasena: str) -> TokenEmitido:
        usuario = self.usuarios.obtener_por_email(email.lower())
        if not self.hasheador.verificar(
            usuario.password_hash if usuario else None, contrasena
        ):
            raise CredencialesInvalidas()
        if not usuario or not usuario.activo:
            raise CredencialesInvalidas()
        return self.sesion.emitir(usuario.id)

    def usuario_desde_token(self, token: str) -> Usuario:
        try:
            usuario = self.usuarios.obtener(self.sesion.sujeto(token))
        except ValueError as error:
            raise CredencialesInvalidas() from error
        if not usuario or not usuario.activo:
            raise CredencialesInvalidas()
        return usuario
