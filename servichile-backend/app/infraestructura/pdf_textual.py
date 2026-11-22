

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.dominio.texto_pdf import MIN_TEXTO_ALNUM, contar_alnum

logger = logging.getLogger(__name__)

def _pagina_tiene_imagenes(page) -> bool:
    try:
        if getattr(page, "images", None) is not None and len(page.images) > 0:
            return True
    except Exception:
        pass
    try:
        resources = page.get("/Resources")
        if resources is None:
            return False
        if hasattr(resources, "get_object"):
            resources = resources.get_object()
        xobj = resources.get("/XObject") if resources else None
        if xobj is None:
            return False
        if hasattr(xobj, "get_object"):
            xobj = xobj.get_object()
        for _name, ref in xobj.items():
            try:
                obj = ref.get_object() if hasattr(ref, "get_object") else ref
                if obj.get("/Subtype") == "/Image":
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False

def extraer_texto_pdf(pdf_bytes: bytes) -> tuple[str, int, bool]:

    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("no-pdf")
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except (PdfReadError, Exception) as error:
        logger.info("PDF ilegible: %s", error)
        raise ValueError("no-pdf") from error

    if reader.is_encrypted:
        try:
            abierto = reader.decrypt("")
        except Exception:
            abierto = 0
        if not abierto:
            raise ValueError("cifrado")

    textos: list[str] = []
    imagenes = 0
    for page in reader.pages:
        try:
            textos.append(page.extract_text() or "")
        except Exception:
            textos.append("")
        if _pagina_tiene_imagenes(page):
            imagenes += 1

    texto = "\n".join(textos).strip()
    alnum = contar_alnum(texto)
    parece_escaneo = alnum < MIN_TEXTO_ALNUM
    if imagenes >= max(1, len(reader.pages)) and alnum < MIN_TEXTO_ALNUM * 3:
        parece_escaneo = True
    return texto, len(reader.pages), parece_escaneo
