

from __future__ import annotations

from app.dominio.aval import ResultadoAval, validar_aval
from app.infraestructura.pdf_textual import extraer_texto_pdf

def _rechazo(motivo: str, *senales: str) -> ResultadoAval:
    return ResultadoAval(
        aceptado=False,
        score=0,
        tipo="otro",
        senales=senales,
        motivo=motivo,
    )

def extraer_texto_pdf_aval(pdf_bytes: bytes) -> tuple[str, int, bool]:
    return extraer_texto_pdf(pdf_bytes)

def analizar_pdf_aval(
    pdf_bytes: bytes,
    *,
    rut_perfil: str | None = None,
    nombre_perfil: str | None = None,
    texto_ya_extraido: str | None = None,
    parece_escaneo: bool | None = None,
    num_paginas: int | None = None,
) -> ResultadoAval:
    if texto_ya_extraido is None:
        try:
            texto, num_paginas, parece_escaneo = extraer_texto_pdf(pdf_bytes)
        except ValueError as err:
            code = str(err)
            if code == "cifrado":
                return _rechazo(
                    "El PDF está cifrado y no se puede validar.", "cifrado"
                )
            return _rechazo("El archivo no es un PDF válido.", "no-pdf")
    else:
        texto = texto_ya_extraido
        parece_escaneo = bool(parece_escaneo)
        num_paginas = int(num_paginas or 1)

    if (num_paginas or 0) < 1:
        return _rechazo("El PDF no tiene páginas.", "vacio")

    if parece_escaneo:
        return _rechazo(
            "Solo se aceptan PDF con texto real seleccionable. "
            "No se admiten fotos dentro del PDF ni escaneos sin capa de texto.",
            "escaneo-o-imagen",
        )

    return validar_aval(
        texto=texto,
        rut_perfil=rut_perfil,
        nombre_perfil=nombre_perfil,
    )

class AnalizadorPdfAval:
    def analizar(
        self,
        contenido: bytes,
        *,
        rut_perfil: str | None = None,
        nombre_perfil: str | None = None,
        nombre_archivo: str | None = None,
    ) -> ResultadoAval:
        del nombre_archivo
        return analizar_pdf_aval(
            contenido,
            rut_perfil=rut_perfil,
            nombre_perfil=nombre_perfil,
        )
