from __future__ import annotations

from urllib.parse import unquote

from app.dominio.entidades import ReporteEmitido, ReporteValidado, Usuario
from app.dominio.errores import ReporteInvalido
from app.dominio.puertos import EmisorReporte, RepositorioUsuarios
from app.servicios.reporte_identidad import ServicioReporteIdentidad

_PREFIJO_PAYLOAD = "servichile://reporte/"

class ServicioReporte:

    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        identidad: ServicioReporteIdentidad,
        emisor: EmisorReporte,
    ) -> None:
        self.usuarios = usuarios
        self.identidad = identidad
        self.emisor = emisor

    def emitir(self, usuario: Usuario) -> ReporteEmitido:
        firmado = self.emisor.emitir(usuario.id)
        estado = self.identidad.estado(usuario)
        return ReporteEmitido(
            payload=_PREFIJO_PAYLOAD + firmado.token,
            token=firmado.token,
            expires_in=firmado.expires_in,
            expires_at=firmado.expires_at,
            nombre=usuario.nombre,
            email=usuario.email,
            nivel_reporte=estado.nivel_reporte,
            estado_reporte=estado.estado_reporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
            antecedentes_verificados=estado.antecedentes_verificados,
            antecedentes_anotaciones=estado.antecedentes_anotaciones,
        )

    def validar(self, escaneado_por: Usuario, payload: str) -> ReporteValidado:
        leido = self.emisor.leer(self._extraer_token(payload))
        titular = self.usuarios.obtener(leido.usuario_id)
        if titular is None or not titular.activo:
            raise ReporteInvalido("No se encontró al titular de este reporte.")
        estado = self.identidad.estado(titular)
        return ReporteValidado(
            es_propio=titular.id == escaneado_por.id,
            nombre=titular.nombre,
            nivel_reporte=estado.nivel_reporte,
            estado_reporte=estado.estado_reporte,
            score_confiabilidad=estado.score_confiabilidad,
            rut_verificado=estado.rut_verificado,
            expires_at=leido.expires_at,
            xp=estado.xp,
            nivel_xp=estado.nivel_xp,
            tipo_cuenta=estado.tipo_cuenta,
            antecedentes_verificados=estado.antecedentes_verificados,
            antecedentes_anotaciones=estado.antecedentes_anotaciones,
        )

    def _extraer_token(self, payload: str) -> str:
        texto = unquote((payload or "").strip())
        if not texto:
            raise ReporteInvalido("No se recibió ningún código QR de reporte.")
        if texto.startswith(_PREFIJO_PAYLOAD):
            return texto[len(_PREFIJO_PAYLOAD) :].strip()
        if texto.count(".") == 2:
            return texto
        raise ReporteInvalido(
            "El código escaneado no es un QR de reporte de ServiChile."
        )
