from __future__ import annotations

import uuid
from datetime import timedelta

import jwt

from app.dominio.entidades import TokenEmitido
from app.tiempo import ahora_utc

_ALGORITHM = "HS256"

class JwtSesion:
    def __init__(self, secreto: str, minutos: int) -> None:
        self.secreto = secreto
        self.minutos = minutos

    def emitir(self, usuario_id: uuid.UUID) -> TokenEmitido:
        expira = timedelta(minutes=self.minutos)
        ahora = ahora_utc()
        token = jwt.encode(
            {"sub": str(usuario_id), "iat": ahora, "exp": ahora + expira},
            self.secreto,
            algorithm=_ALGORITHM,
        )
        return TokenEmitido(
            access_token=token, expires_in=int(expira.total_seconds())
        )

    def sujeto(self, token: str) -> uuid.UUID:
        try:
            datos = jwt.decode(
                token,
                self.secreto,
                algorithms=[_ALGORITHM],
                options={"require": ["sub", "exp"]},
            )
            return uuid.UUID(datos["sub"])
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise ValueError("token de sesión inválido") from error
