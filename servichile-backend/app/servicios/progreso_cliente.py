

from __future__ import annotations

import uuid

from app.dominio import progreso_cliente as reglas

from app.dominio.entidades import Usuario

from app.dominio.puertos import RepositorioXp

class ServicioProgresoCliente:

    def __init__(self, xp: RepositorioXp) -> None:

        self.xp = xp

    def por_registro(self, usuario_id: uuid.UUID) -> int:

        return self.xp.otorgar(usuario_id, reglas.EVENTO_REGISTRO, reglas.XP_REGISTRO)

    def por_perfil_basico(self, usuario: Usuario) -> int:

        edad_ok = usuario.perfil is not None and usuario.perfil.edad is not None

        tel_ok = bool(usuario.telefono and str(usuario.telefono).strip())

        if not (edad_ok and tel_ok):

            return 0

        return self.xp.otorgar(
            usuario.id, reglas.EVENTO_PERFIL_BASICO, reglas.XP_PERFIL_BASICO
        )

    def por_rut(self, usuario_id: uuid.UUID) -> int:

        return self.xp.otorgar(usuario_id, reglas.EVENTO_RUT, reglas.XP_RUT)

    def por_biometria(self, usuario_id: uuid.UUID) -> int:

        return self.xp.otorgar(usuario_id, reglas.EVENTO_BIOMETRIA, reglas.XP_BIOMETRIA)

    def por_antecedentes(self, usuario_id: uuid.UUID) -> int:

        return self.xp.otorgar(
            usuario_id, reglas.EVENTO_ANTECEDENTES, reglas.XP_ANTECEDENTES
        )

    def por_aval(self, usuario_id: uuid.UUID) -> int:

        return self.xp.otorgar(usuario_id, reglas.EVENTO_AVAL, reglas.XP_AVAL)

    def por_trabajo_concretado(
        self, usuario_id: uuid.UUID, trabajo_id: uuid.UUID
    ) -> int:

        return self.xp.otorgar(
            usuario_id,
            reglas.evento_trabajo_concretado(str(trabajo_id)),
            reglas.XP_TRABAJO_CONCRETADO,
        )

    def total(self, usuario_id: uuid.UUID) -> int:

        return self.xp.total(usuario_id)
