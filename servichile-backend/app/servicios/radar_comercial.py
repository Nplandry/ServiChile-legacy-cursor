

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.dominio.entidades import Usuario
from app.dominio.errores import CorreoRechazado, NegocioNoEncontrado
from app.dominio.puertos import (
    EmisorReporte,
    EnviadorPlataforma,
    MensajeSaliente,
    RepositorioCorreo,
    RepositorioNegocios,
    RepositorioUsuarios,
)
from app.servicios.negocio_reputacion import reputacion_de

_PREFIJO_QR = "servichile://reporte/"

@dataclass(frozen=True)
class ResultadoInforme:
    enviado: bool
    destino: str
    qr_payload: str | None
    qr_expira: datetime | None

class ServicioRadarComercial:
    def __init__(
        self,
        negocios: RepositorioNegocios,
        usuarios: RepositorioUsuarios,
        correo: RepositorioCorreo,
        enviador: EnviadorPlataforma,
        emisor: EmisorReporte,
    ) -> None:
        self.negocios = negocios
        self.usuarios = usuarios
        self.correo = correo
        self.enviador = enviador
        self.emisor = emisor

    def informe(self, usuario: Usuario, negocio_id: uuid.UUID) -> ResultadoInforme:
        negocio = self.negocios.obtener(negocio_id)
        if negocio is None:
            raise NegocioNoEncontrado
        rep = reputacion_de(negocio)
        qr_payload = None
        qr_expira = None
        if negocio.reclamado_por is not None:
            titular = self.usuarios.obtener(negocio.reclamado_por)
            if titular is not None and titular.activo:
                firmado = self.emisor.emitir(titular.id)
                qr_payload = _PREFIJO_QR + firmado.token
                qr_expira = firmado.expires_at

        destino = usuario.email
        asunto = f"Reporte de transparencia — {negocio.nombre}"[:200]
        cuerpo = (
            f"Hola {usuario.nombre},\n\n"
            f"Compró el reporte de transparencia de {negocio.nombre}.\n"
            f"Índice global: {float(rep.indice_transparencia):.1f} / 10 "
            f"({int(rep.indice_pct)}% señales).\n"
            f"Documentos legales: {int(rep.docs_verificados)} de {int(rep.docs_total)}.\n\n"
            "El informe completo con el diseño ServiChile se abre en la aplicación "
            "para guardarlo en PDF desde el navegador.\n"
            "Este correo es el comprobante enviado a la cuenta con la que se registró.\n\n"
            "ServiChile"
        )

        if not self.enviador.disponible():
            return ResultadoInforme(
                enviado=False,
                destino=destino,
                qr_payload=qr_payload,
                qr_expira=qr_expira,
            )
        try:
            self.enviador.enviar(
                MensajeSaliente(destino=destino, asunto=asunto, cuerpo=cuerpo)
            )
        except CorreoRechazado:
            return ResultadoInforme(
                enviado=False,
                destino=destino,
                qr_payload=qr_payload,
                qr_expira=qr_expira,
            )
        self.correo.registrar(
            usuario.id, negocio.id, "reporte", destino, asunto, cuerpo, "enviado"
        )
        return ResultadoInforme(
            enviado=True,
            destino=destino,
            qr_payload=qr_payload,
            qr_expira=qr_expira,
        )
