from app.dominio.entidades import Perfil, Usuario

CAMPOS_PERFIL = {"edad", "tipo_cuenta"}

def aplicar_perfil(usuario: Usuario, cambios: dict) -> None:

    relevantes = {
        campo: valor for campo, valor in cambios.items() if campo in CAMPOS_PERFIL
    }

    if not relevantes:

        return

    if usuario.perfil is None:

        usuario.perfil = Perfil()

    for campo, valor in relevantes.items():

        setattr(usuario.perfil, campo, valor)
