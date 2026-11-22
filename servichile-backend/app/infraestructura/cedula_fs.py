

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.dominio.cedula import (
    CEDULA_CONTENT_TYPE,
    CEDULA_JPEG_QUALITY_DEFAULT,
    CEDULA_MAX_LADO_DEFAULT,
    MetaCedula,
)
from app.dominio.errores import CedulaInvalida

class AlmacenamientoCedulaLocal:
    def __init__(
        self,
        raiz: Path,
        *,
        max_lado: int = CEDULA_MAX_LADO_DEFAULT,
        calidad_jpeg: int = CEDULA_JPEG_QUALITY_DEFAULT,
    ) -> None:
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.max_lado = max(400, int(max_lado))
        self.calidad_jpeg = min(95, max(50, int(calidad_jpeg)))

    def preparar_en_memoria(self, contenido: bytes) -> tuple[bytes, MetaCedula]:

        jpeg, ancho, alto = self._comprimir(contenido)
        meta = MetaCedula(
            ruta_relativa="",
            sha256=hashlib.sha256(jpeg).hexdigest(),
            bytes_=len(jpeg),
            ancho=ancho,
            alto=alto,
            content_type=CEDULA_CONTENT_TYPE,
        )
        return jpeg, meta

    def guardar(self, usuario_id: uuid.UUID, contenido: bytes) -> MetaCedula:
        jpeg, meta = self.preparar_en_memoria(contenido)
        nombre = f"{usuario_id}.jpg"
        (self.raiz / nombre).write_bytes(jpeg)
        return MetaCedula(
            ruta_relativa=nombre,
            sha256=meta.sha256,
            bytes_=meta.bytes_,
            ancho=meta.ancho,
            alto=meta.alto,
            content_type=meta.content_type,
        )

    def leer(self, ruta_relativa: str) -> bytes:
        ruta = self.raiz / Path(ruta_relativa).name
        if not ruta.is_file() or ruta.resolve().parent != self.raiz.resolve():
            raise CedulaInvalida("No se encontró la foto del carnet guardada.")
        return ruta.read_bytes()

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
            raise CedulaInvalida(
                "No se pudo leer la foto del carnet. Use JPEG o PNG nítido."
            ) from error

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")

        img.thumbnail((self.max_lado, self.max_lado), Image.Resampling.BILINEAR)
        buf = io.BytesIO()
        img.save(
            buf,
            format="JPEG",
            quality=self.calidad_jpeg,
            optimize=True,
        )
        data = buf.getvalue()
        if len(data) < 1500 or img.width < 320 or img.height < 200:
            raise CedulaInvalida(
                "La foto del carnet es demasiado pequeña o borrosa. Encuadre el frente completo."
            )
        return data, img.width, img.height
