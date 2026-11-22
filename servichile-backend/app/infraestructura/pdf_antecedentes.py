from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.dominio.antecedentes import (
    ResultadoAntecedentes,
    validar_certificado_antecedentes,
)
from app.dominio.texto_pdf import MIN_TEXTO_ALNUM, contar_alnum
from app.infraestructura.pades import verificar_firma_pades
from app.infraestructura.pdf_textual import extraer_texto_pdf

def _parse_pdf_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", str(raw).strip())
    if not m:
        return None
    y, mo, d, h, mi, s = (int(x) for x in m.groups())
    try:
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None

def _rechazo(
    motivo: str,
    *senales: str,
    sha256_hash: str | None = None,
) -> ResultadoAntecedentes:
    return ResultadoAntecedentes(
        aceptado=False,
        score=0,
        anotaciones=None,
        folio=None,
        codigo=None,
        run=None,
        senales=senales,
        motivo=motivo,
        sha256_hash=sha256_hash,
    )

def analizar_pdf_antecedentes(
    pdf_bytes: bytes,
    nombre_archivo: str | None = None,
    *,
    ca_pem_path: str | None = None,
) -> ResultadoAntecedentes:
    pades = verificar_firma_pades(
        pdf_bytes, perfil="antecedentes", ca_pem_path=ca_pem_path
    )
    if not pades.ok:
        return _rechazo(
            pades.motivo,
            *pades.senales,
            sha256_hash=pades.sha256_hash,
        )

    bytes_texto = pades.pdf_firmado_bytes or pdf_bytes
    try:
        texto, num_paginas, escaneo = extraer_texto_pdf(bytes_texto)
    except ValueError:
        try:
            texto, num_paginas, escaneo = extraer_texto_pdf(pdf_bytes)
        except ValueError as err:
            code = str(err)
            if code == "cifrado":
                return _rechazo(
                    "El PDF está cifrado y no se puede validar.",
                    "cifrado",
                    sha256_hash=pades.sha256_hash,
                )
            return _rechazo(
                "El archivo no es un PDF válido.",
                "no-pdf",
                sha256_hash=pades.sha256_hash,
            )

    if escaneo or contar_alnum(texto) < MIN_TEXTO_ALNUM:
        return _rechazo(
            "Solo se aceptan PDF con texto seleccionable del Registro Civil. "
            "No se admiten fotos ni escaneos sin capa de texto.",
            "escaneo-o-imagen",
            sha256_hash=pades.sha256_hash,
        )

    producer = None
    creation = None
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        meta = reader.metadata
        if meta is not None:
            producer = getattr(meta, "producer", None) or meta.get("/Producer")
            creation_raw = getattr(meta, "creation_date", None)
            if creation_raw is None:
                creation = _parse_pdf_date(meta.get("/CreationDate"))
            elif isinstance(creation_raw, datetime):
                creation = creation_raw.replace(tzinfo=None)
            else:
                creation = _parse_pdf_date(str(creation_raw))
    except (PdfReadError, Exception):
        pass

    return validar_certificado_antecedentes(
        nombre_archivo=nombre_archivo,
        meta_creation=creation,
        producer=str(producer) if producer else None,
        num_paginas=num_paginas,
        texto=texto,
        texto_real=True,
        pades_ok=True,
        entidad_emisora=pades.entidad_emisora,
        sha256_hash=pades.sha256_hash,
    )

class AnalizadorPdfAntecedentes:
    def __init__(self, ca_pem_path: str | None = None) -> None:
        self._ca_pem_path = ca_pem_path

    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes:
        return analizar_pdf_antecedentes(
            contenido, nombre_archivo, ca_pem_path=self._ca_pem_path
        )
