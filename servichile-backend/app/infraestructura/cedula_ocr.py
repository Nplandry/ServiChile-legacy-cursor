

from __future__ import annotations

import io
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from PIL import Image, ImageFilter, ImageOps

from app.dominio.cedula import ResultadoCedula, validar_cedula, _extraer_ruts
from app.dominio.errores import CedulaInvalida
from app.infraestructura.cedula_vision import (
    UMBRAL_FACE_DEFAULT,
    ComparadorRostrosOpenCv,
    enderezar_carnet,
    recortes_roi_run_pil,
)

logger = logging.getLogger(__name__)

_OCR_MAX_LADO = 1400

_SCORE_SUFICIENTE = 70

def _score_texto(texto: str) -> int:
    t = texto or ""
    compact = re.sub(r"[^a-z0-9]", "", t.lower())
    score = 0
    if _extraer_ruts(t):
        score += 50
    if "republicadechile" in compact or "chile" in compact:
        score += 15
    if "identidad" in compact or "cedula" in compact or "cédula" in t.lower():
        score += 10
    if "chilena" in compact or "nacionalidad" in compact:
        score += 8
    if "vencimiento" in compact or "nacimiento" in compact:
        score += 8
    if re.search(r"B[0-9A-Z]\w?\.\d{3}\.\d{3}", t, re.I):
        score += 5
    score += min(20, len(t.strip()) // 40)
    return score

@lru_cache(maxsize=1)
def _langs_disponibles() -> tuple[str, ...]:

    try:
        import pytesseract

        disponibles = set()
        try:
            raw = pytesseract.get_languages(config="")
            disponibles = {str(x).lower() for x in raw}
        except Exception:
            pass
        orden: list[str] = []
        if "spa" in disponibles and "eng" in disponibles:
            orden.append("spa+eng")
        elif "spa" in disponibles:
            orden.append("spa")
        if "eng" in disponibles and "eng" not in orden:
            orden.append("eng")
        return tuple(orden) or ("eng",)
    except Exception:
        return ("eng",)

def _preprocesar(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    m = max(w, h)
    if m < 1000:

        scale = 1200 / m
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    elif m > _OCR_MAX_LADO:
        scale = _OCR_MAX_LADO / m
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    gris = ImageOps.autocontrast(img.convert("L"))
    return gris.filter(ImageFilter.SHARPEN)

def _tesseract_string(gris: Image.Image, *, lang: str, psm: int, whitelist: str | None = None) -> str:
    import pytesseract

    config = f"--oem 3 --psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    return pytesseract.image_to_string(gris, lang=lang, config=config) or ""

def _ocr_rapido(gris: Image.Image) -> str:

    langs = _langs_disponibles()
    lang = langs[0]
    candidatos: list[tuple[int, str]] = []

    for psm in (4, 3):
        try:
            texto = _tesseract_string(gris, lang=lang, psm=psm)
        except Exception as err:
            logger.info("OCR lang=%s psm=%s: %s", lang, psm, err)

            if len(langs) > 1 and lang == langs[0]:
                lang = langs[1]
                try:
                    texto = _tesseract_string(gris, lang=lang, psm=psm)
                except Exception as err2:
                    logger.info("OCR fallback lang=%s: %s", lang, err2)
                    continue
            else:
                continue
        if not texto.strip():
            continue
        sc = _score_texto(texto)
        candidatos.append((sc, texto))
        if sc >= _SCORE_SUFICIENTE and _extraer_ruts(texto):
            break

    if not candidatos:

        for lang2 in langs:
            try:
                texto = _tesseract_string(gris, lang=lang2, psm=11)
            except Exception:
                continue
            if texto.strip():
                candidatos.append((_score_texto(texto), texto))
                break
        if not candidatos:
            return ""

    candidatos.sort(key=lambda x: x[0], reverse=True)
    mejor = candidatos[0][1]

    if (
        "vencimiento" not in mejor.lower()
        or "nacionalidad" not in mejor.lower()
    ) and candidatos[0][0] < 85:
        try:
            extra = _tesseract_string(gris, lang=lang, psm=11)
            if extra.strip() and (
                "vencimiento" in extra.lower() or "nacionalidad" in extra.lower()
            ):
                mejor = mejor + "\n" + extra
        except Exception:
            pass
    return mejor

def _ocr_roi_run(gris_full: Image.Image) -> str:

    for crop in recortes_roi_run_pil(gris_full):
        gris = ImageOps.autocontrast(crop)
        for psm in (7, 8):
            try:
                texto = _tesseract_string(
                    gris, lang="eng", psm=psm, whitelist="0123456789Kk.-"
                )
            except Exception:
                continue
            if _extraer_ruts(texto):
                return texto.strip()
            if (texto or "").strip():

                pass
    return ""

class LectorOcrTesseract:

    def extraer_texto(self, jpeg_bytes: bytes) -> str:
        try:
            import pytesseract
        except ImportError as error:
            raise CedulaInvalida(
                "OCR no disponible (falta pytesseract). Instale la dependencia."
            ) from error

        try:

            img = Image.open(io.BytesIO(jpeg_bytes))
            gris = _preprocesar(img)
            mejor = _ocr_rapido(gris)
            if not _extraer_ruts(mejor):
                roi = _ocr_roi_run(gris)
                if roi:
                    mejor = (mejor + "\nRUN\n" + roi).strip()
            return mejor
        except CedulaInvalida:
            raise
        except Exception as error:
            logger.warning("tesseract falló: %s", error)
            raise CedulaInvalida(
                "No se pudo leer el texto del carnet. Instale Tesseract "
                "(brew install tesseract tesseract-lang) y use una foto nítida del frente."
            ) from error

class LectorOcrFijo:

    def __init__(self, texto: str) -> None:
        self.texto = texto

    def extraer_texto(self, jpeg_bytes: bytes) -> str:
        return self.texto

class AnalizadorCedulaOcr:
    def __init__(
        self, lector, comparador=None, *, umbral_face: float = UMBRAL_FACE_DEFAULT
    ) -> None:
        self.lector = lector
        self.comparador = comparador or ComparadorRostrosOpenCv()
        self.umbral_face = float(umbral_face)

    def analizar(
        self,
        jpeg_bytes: bytes,
        *,
        ancho: int,
        alto: int,
        bytes_: int,
        rut_perfil: str | None = None,
        nombre_perfil: str | None = None,
        rut_perfil_verificado: bool = False,
        selfie_jpeg: bytes | None = None,
    ) -> ResultadoCedula:
        fijo = isinstance(self.lector, LectorOcrFijo)
        recto = jpeg_bytes if fijo else enderezar_carnet(jpeg_bytes)
        if not fijo:
            try:
                with Image.open(io.BytesIO(recto)) as img:
                    img.load()
                    ancho, alto = img.size
            except Exception:
                pass

        if selfie_jpeg and not fijo:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_texto = pool.submit(self.lector.extraer_texto, recto)
                fut_face = pool.submit(self.comparador.comparar, recto, selfie_jpeg)
                texto = fut_texto.result()
                face_score = float(fut_face.result())
        else:
            texto = self.lector.extraer_texto(recto if not fijo else jpeg_bytes)
            face_score = None
            if selfie_jpeg:
                face_score = float(self.comparador.comparar(recto, selfie_jpeg))

        return validar_cedula(
            texto_ocr=texto,
            ancho=ancho,
            alto=alto,
            bytes_=bytes_,
            rut_perfil=rut_perfil,
            nombre_perfil=nombre_perfil,
            rut_perfil_verificado=rut_perfil_verificado,
            face_score=face_score,
            umbral_face=self.umbral_face,
        )
