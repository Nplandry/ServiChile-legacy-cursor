

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.dominio.biometria import (
    BIOMETRIA_CONTENT_TYPE,
    BIOMETRIA_JPEG_QUALITY_DEFAULT,
    BIOMETRIA_MAX_LADO_DEFAULT,
    MetaBiometria,
)
from app.dominio.errores import BiometriaInvalida

class AlmacenamientoBiometriaLocal:
    def __init__(
        self,
        raiz: Path,
        *,
        max_lado: int = BIOMETRIA_MAX_LADO_DEFAULT,
        calidad_jpeg: int = BIOMETRIA_JPEG_QUALITY_DEFAULT,
    ) -> None:
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.max_lado = max(64, int(max_lado))
        self.calidad_jpeg = min(95, max(40, int(calidad_jpeg)))

    def guardar(self, usuario_id: uuid.UUID, contenido: bytes) -> MetaBiometria:
        jpeg, ancho, alto = self._comprimir(contenido)
        nombre = f"{usuario_id}.jpg"
        destino = self.raiz / nombre
        destino.write_bytes(jpeg)
        return MetaBiometria(
            ruta_relativa=nombre,
            sha256=hashlib.sha256(jpeg).hexdigest(),
            bytes_=len(jpeg),
            ancho=ancho,
            alto=alto,
            content_type=BIOMETRIA_CONTENT_TYPE,
        )

    def leer(self, ruta_relativa: str) -> bytes:
        base = Path(ruta_relativa).name
        if not base:
            raise BiometriaInvalida("Selfie biométrica no encontrada.")
        ruta = self.raiz / base
        if not ruta.is_file() or ruta.resolve().parent != self.raiz.resolve():
            raise BiometriaInvalida(
                "No hay selfie biométrica guardada. Complete la verificación facial primero."
            )
        data = ruta.read_bytes()
        if len(data) < 200:
            raise BiometriaInvalida("La selfie biométrica está corrupta. Vuelva a capturarla.")
        return data

    def eliminar(
        self, usuario_id: uuid.UUID, ruta_relativa: str | None = None
    ) -> None:
        candidatos = {f"{usuario_id}.jpg"}
        if ruta_relativa:
            base = Path(ruta_relativa).name
            if base:
                candidatos.add(base)
        for nombre in candidatos:
            ruta = self.raiz / nombre
            if ruta.is_file() and ruta.resolve().parent == self.raiz.resolve():
                try:
                    ruta.unlink()
                except OSError:
                    pass

    def _comprimir(self, contenido: bytes) -> tuple[bytes, int, int]:
        try:
            img = Image.open(io.BytesIO(contenido))
            img.load()
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise BiometriaInvalida(
                "No se pudo leer la foto. Use JPEG o PNG nítido."
            ) from error

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        img.thumbnail((self.max_lado, self.max_lado), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(
            buf,
            format="JPEG",
            quality=self.calidad_jpeg,
            optimize=True,
            progressive=True,
        )
        data = buf.getvalue()
        if len(data) < 200:
            raise BiometriaInvalida("La foto es demasiado pequeña o inválida.")
        return data, img.width, img.height
