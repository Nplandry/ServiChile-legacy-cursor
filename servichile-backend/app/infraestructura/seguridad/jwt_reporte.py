from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.dominio.errores import ReporteInvalido
from app.dominio.puertos import TokenReporteFirmado, TokenReporteLeido
from app.tiempo import ahora_utc

_ALGORITHM = "HS256"
_PROPOSITO = "reporte"

class JwtReporte:
    def __init__(self, secreto: str, minutos: int) -> None:
        self.secreto = secreto
        self.minutos = minutos

    def emitir(self, usuario_id: uuid.UUID) -> TokenReporteFirmado:
        ahora = ahora_utc()
        expira = timedelta(minutes=self.minutos)
        expires_at = ahora + expira
        token = jwt.encode(
            {
                "sub": str(usuario_id),
                "pur": _PROPOSITO,
                "iat": ahora,
                "exp": expires_at,
            },
            self.secreto,
            algorithm=_ALGORITHM,
        )
        return TokenReporteFirmado(
            token=token,
            expires_in=int(expira.total_seconds()),
            expires_at=expires_at,
        )

    def leer(self, token: str) -> TokenReporteLeido:
        try:
            datos = jwt.decode(
                token,
                self.secreto,
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp", "pur"]},
            )
        except jwt.ExpiredSignatureError as error:
            raise ReporteInvalido(
                "Este QR del reporte ya expiró. Pida al titular que lo renueve."
            ) from error
        except jwt.PyJWTError as error:
            raise ReporteInvalido("QR de reporte inválido o alterado.") from error

        if datos.get("pur") != _PROPOSITO:
            raise ReporteInvalido("Este código no es un reporte firmado de ServiChile.")

        try:
            usuario_id = uuid.UUID(str(datos["sub"]))
        except (ValueError, TypeError) as error:
            raise ReporteInvalido("QR de reporte inválido o alterado.") from error

        expires_at = ahora_utc()
        exp = datos.get("exp")
        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp, tz=UTC)

        return TokenReporteLeido(usuario_id=usuario_id, expires_at=expires_at)
