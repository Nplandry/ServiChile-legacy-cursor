

from __future__ import annotations

from app.dominio.docs_empresa import (
    TIPOS_PADES,
    ResultadoDocEmpresa,
    TipoDocEmpresa,
    label_tipo,
    perfil_pades_de,
    validar_doc_empresa,
)
from app.infraestructura.pades import verificar_firma_pades
from app.infraestructura.pdf_textual import extraer_texto_pdf

def _rechazo(
    tipo: TipoDocEmpresa,
    motivo: str,
    *senales: str,
    sha256_hash: str | None = None,
    grupo: int = 1,
) -> ResultadoDocEmpresa:
    return ResultadoDocEmpresa(
        aceptado=False,
        score=0,
        tipo=tipo,
        senales=senales,
        motivo=motivo,
        sha256_hash=sha256_hash,
        grupo=grupo,
    )

class AnalizadorPdfDocEmpresa:
    def __init__(self, ca_pem_path: str | None = None) -> None:
        self._ca_pem_path = ca_pem_path

    def analizar(
        self,
        contenido: bytes,
        *,
        tipo: TipoDocEmpresa,
        rut_empresa: str | None = None,
        nombre_empresa: str | None = None,
        nombre_archivo: str | None = None,
    ) -> ResultadoDocEmpresa:
        del nombre_archivo
        pades_ok = False
        entidad_emisora = None
        sha256_hash = None
        bytes_texto = contenido

        if tipo in TIPOS_PADES:
            perfil = perfil_pades_de(tipo) or tipo
            pades = verificar_firma_pades(
                contenido, perfil=perfil, ca_pem_path=self._ca_pem_path
            )
            sha256_hash = pades.sha256_hash
            if not pades.ok:
                return _rechazo(
                    tipo,
                    pades.motivo,
                    *pades.senales,
                    sha256_hash=pades.sha256_hash,
                    grupo=1,
                )
            pades_ok = True
            entidad_emisora = pades.entidad_emisora

            bytes_texto = pades.pdf_firmado_bytes or contenido

        try:
            texto, num_paginas, escaneo = extraer_texto_pdf(bytes_texto)
        except ValueError as err:
            code = str(err)
            if code == "cifrado":
                return _rechazo(
                    tipo,
                    "El PDF está cifrado y no se puede validar.",
                    "cifrado",
                    sha256_hash=sha256_hash,
                )

            if tipo in TIPOS_PADES and pades_ok:
                try:
                    texto, num_paginas, escaneo = extraer_texto_pdf(contenido)
                except ValueError:
                    return _rechazo(
                        tipo,
                        "El archivo no es un PDF válido.",
                        "no-pdf",
                        sha256_hash=sha256_hash,
                    )
            else:
                return _rechazo(
                    tipo,
                    "El archivo no es un PDF válido.",
                    "no-pdf",
                    sha256_hash=sha256_hash,
                )

        if num_paginas < 1:
            return _rechazo(
                tipo, "El PDF no tiene páginas.", "vacio", sha256_hash=sha256_hash
            )

        if escaneo:
            return _rechazo(
                tipo,
                f"Solo se aceptan PDF con texto real para {label_tipo(tipo)}. "
                "No se admiten fotos ni escaneos sin capa de texto.",
                "escaneo-o-imagen",
                sha256_hash=sha256_hash,
            )

        return validar_doc_empresa(
            tipo=tipo,
            texto=texto,
            rut_empresa=rut_empresa,
            nombre_empresa=nombre_empresa,
            pades_ok=pades_ok,
            entidad_emisora=entidad_emisora,
            sha256_hash=sha256_hash,
        )
