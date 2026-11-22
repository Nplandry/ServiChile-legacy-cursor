

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.dominio.errores import CorreoRechazado
from app.dominio.puertos import EnviadorPlataforma, MensajeSaliente

log = logging.getLogger(__name__)

class EnviadorMemoria(EnviadorPlataforma):

    def __init__(self, simular: bool) -> None:
        self._simular = simular
        self.enviados: list[MensajeSaliente] = []

    def disponible(self) -> bool:
        return self._simular

    def enviar(self, mensaje: MensajeSaliente) -> None:
        if not self._simular:
            raise CorreoRechazado("ServiChile no tiene configurado el correo de salida.")
        self.enviados.append(mensaje)

class EnviadorSmtp(EnviadorPlataforma):
    def __init__(
        self,
        host: str,
        puerto: int,
        usuario: str,
        clave: str,
        desde: str,
        *,
        starttls: bool = True,
    ) -> None:
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.clave = clave
        self.desde = desde
        self.starttls = starttls

    def disponible(self) -> bool:
        return bool(self.host and self.desde)

    def enviar(self, mensaje: MensajeSaliente) -> None:
        correo = EmailMessage()
        correo["From"] = self.desde
        correo["To"] = mensaje.destino
        correo["Subject"] = mensaje.asunto
        correo.set_content(mensaje.cuerpo)
        try:
            with smtplib.SMTP(self.host, self.puerto, timeout=15) as smtp:
                if self.starttls:
                    smtp.starttls()
                if self.usuario:
                    smtp.login(self.usuario, self.clave)
                smtp.send_message(correo)
        except (OSError, smtplib.SMTPException) as error:
            log.info("smtp rechazado: %s", type(error).__name__)
            raise CorreoRechazado(
                "No se pudo enviar el reporte al correo de la cuenta."
            ) from error
