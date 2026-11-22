

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Protocol

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

UMBRAL_FACE_DEFAULT = 0.52

_FOTO_CARNET = (0.04, 0.14, 0.38, 0.72)

_ROIS_RUN = (
    (0.02, 0.76, 0.52, 0.98),
    (0.02, 0.70, 0.48, 0.95),
)

_DETECT_MAX = 640

_WARP_MAX = 1600

_FACE_DETECT_MAX = 480

class ComparadorRostros(Protocol):
    def comparar(self, carnet_jpeg: bytes, selfie_jpeg: bytes) -> float: ...

def _jpeg_a_bgr(jpeg_bytes: bytes):
    import cv2

    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("imagen inválida")
    return bgr

def _bgr_a_jpeg(bgr, quality: int = 88) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("no se pudo re-encodear")
    return bytes(buf)

def _limitar_lado(bgr, max_lado: int, *, interp=None):
    import cv2

    h, w = bgr.shape[:2]
    m = max(h, w)
    if m <= max_lado:
        return bgr, 1.0
    escala = max_lado / m
    if interp is None:
        interp = cv2.INTER_AREA if escala < 1.0 else cv2.INTER_LINEAR
    out = cv2.resize(bgr, (int(w * escala), int(h * escala)), interpolation=interp)
    return out, escala

def _orden_puntos(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).ravel()
    orden = np.zeros((4, 2), dtype=np.float32)
    orden[0] = pts[np.argmin(s)]
    orden[2] = pts[np.argmax(s)]
    orden[1] = pts[np.argmin(diff)]
    orden[3] = pts[np.argmax(diff)]
    return orden

def enderezar_carnet(jpeg_bytes: bytes) -> bytes:

    try:
        import cv2
    except ImportError:
        return jpeg_bytes

    try:
        bgr = _jpeg_a_bgr(jpeg_bytes)
    except ValueError:
        return jpeg_bytes

    h, w = bgr.shape[:2]
    if min(h, w) < 120:
        return jpeg_bytes

    small, escala = _limitar_lado(bgr, _DETECT_MAX)
    gris = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gris = cv2.GaussianBlur(gris, (3, 3), 0)
    edges = cv2.Canny(gris, 60, 160)
    contornos, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_img = float(small.shape[0] * small.shape[1])
    mejor = None
    mejor_area = 0.0
    for c in contornos:
        area = float(cv2.contourArea(c))
        if area < area_img * 0.28 or area > area_img * 0.97:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.025 * peri, True)
        if len(approx) != 4:
            continue
        if area > mejor_area:
            mejor_area = area
            mejor = approx.reshape(4, 2).astype(np.float32)

    if mejor is None:
        if not contornos:
            return jpeg_bytes
        c = max(contornos, key=cv2.contourArea)
        if cv2.contourArea(c) < area_img * 0.25:
            return jpeg_bytes
        rect = cv2.minAreaRect(c)
        angulo = rect[-1]
        if angulo < -45:
            angulo = 90 + angulo
        if abs(angulo) < 2.0 or abs(angulo) > 20:
            return jpeg_bytes

        base, _ = _limitar_lado(bgr, _WARP_MAX)
        bh, bw = base.shape[:2]
        M = cv2.getRotationMatrix2D((bw / 2, bh / 2), angulo, 1.0)
        recto = cv2.warpAffine(
            base, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
        )
        try:
            return _bgr_a_jpeg(recto)
        except ValueError:
            return jpeg_bytes

    pts = _orden_puntos(mejor / escala)
    (tl, tr, br, bl) = pts
    ancho_a = float(np.linalg.norm(br - bl))
    ancho_b = float(np.linalg.norm(tr - tl))
    alto_a = float(np.linalg.norm(tr - br))
    alto_b = float(np.linalg.norm(tl - bl))
    ancho_max = max(int(ancho_a), int(ancho_b), 200)
    alto_max = max(int(alto_a), int(alto_b), 120)

    m = max(ancho_max, alto_max)
    if m > _WARP_MAX:
        s = _WARP_MAX / m
        ancho_max = max(200, int(ancho_max * s))
        alto_max = max(120, int(alto_max * s))
    destino = np.array(
        [[0, 0], [ancho_max - 1, 0], [ancho_max - 1, alto_max - 1], [0, alto_max - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(pts, destino)
    warpped = cv2.warpPerspective(
        bgr, M, (ancho_max, alto_max), flags=cv2.INTER_LINEAR
    )
    try:
        return _bgr_a_jpeg(warpped)
    except ValueError:
        return jpeg_bytes

def recortes_roi_run_pil(img: Image.Image) -> list[Image.Image]:

    if img.mode != "L":
        base = img.convert("L")
    else:
        base = img
    w, h = base.size
    out: list[Image.Image] = []
    for x0, y0, x1, y1 in _ROIS_RUN:
        caja = (int(w * x0), int(h * y0), int(w * x1), int(h * y1))
        if caja[2] - caja[0] < 40 or caja[3] - caja[1] < 20:
            continue
        crop = base.crop(caja)
        cw, ch = crop.size
        if max(cw, ch) < 360:
            s = 360 / max(cw, ch)
            crop = crop.resize((int(cw * s), int(ch * s)), Image.Resampling.BILINEAR)
        out.append(crop)
    return out

@lru_cache(maxsize=1)
def _cascade_frontal():
    import cv2

    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(path)

def _detectar_rostro(bgr, escala_min: float = 0.12):
    import cv2

    small, escala = _limitar_lado(bgr, _FACE_DETECT_MAX)
    gris = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gris = cv2.equalizeHist(gris)
    cascade = _cascade_frontal()
    h, w = gris.shape[:2]
    min_lado = max(24, int(min(h, w) * escala_min))
    faces = cascade.detectMultiScale(
        gris,
        scaleFactor=1.15,
        minNeighbors=4,
        minSize=(min_lado, min_lado),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])

    if escala != 1.0:
        inv = 1.0 / escala
        x = int(x * inv)
        y = int(y * inv)
        fw = int(fw * inv)
        fh = int(fh * inv)
        gris_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        gris_full = gris
    pad = int(0.12 * max(fw, fh))
    H, W = gris_full.shape[:2]
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(W, x + fw + pad)
    y1 = min(H, y + fh + pad)
    return gris_full[y0:y1, x0:x1]

def _roi_foto_carnet(bgr):
    import cv2

    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = _FOTO_CARNET
    crop = bgr[int(h * y0) : int(h * y1), int(w * x0) : int(w * x1)]
    if crop.size == 0:
        return None
    cara = _detectar_rostro(crop, escala_min=0.18)
    if cara is not None:
        return cara
    return cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

def _normalizar_cara(gris, lado: int = 96) -> np.ndarray:
    import cv2

    if gris is None or gris.size == 0:
        raise ValueError("sin cara")
    cara = cv2.resize(gris, (lado, lado), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(cara)

def _similitud_caras(a: np.ndarray, b: np.ndarray) -> float:
    import cv2

    af = a.astype(np.float32).ravel()
    bf = b.astype(np.float32).ravel()
    af = (af - af.mean()) / (af.std() + 1e-6)
    bf = (bf - bf.mean()) / (bf.std() + 1e-6)
    cos = float(np.dot(af, bf) / max(1, len(af)))
    cos01 = max(0.0, min(1.0, (cos + 1.0) / 2.0))

    ha = cv2.calcHist([a], [0], None, [64], [0, 256])
    hb = cv2.calcHist([b], [0], None, [64], [0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    corr = float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))
    corr01 = max(0.0, min(1.0, corr))
    return 0.65 * cos01 + 0.35 * corr01

class ComparadorRostrosOpenCv:

    def comparar(self, carnet_jpeg: bytes, selfie_jpeg: bytes) -> float:
        try:
            import cv2
        except ImportError:
            logger.warning("opencv no instalado; face-match = 0")
            return 0.0
        try:
            carnet = _jpeg_a_bgr(carnet_jpeg)
            selfie = _jpeg_a_bgr(selfie_jpeg)
            cara_carnet = _roi_foto_carnet(carnet)
            cara_selfie = _detectar_rostro(selfie, escala_min=0.15)
            if cara_selfie is None:
                h, w = selfie.shape[:2]
                m = int(min(h, w) * 0.55)
                y0 = max(0, (h - m) // 2 - int(h * 0.05))
                x0 = max(0, (w - m) // 2)
                import cv2

                cara_selfie = cv2.cvtColor(
                    selfie[y0 : y0 + m, x0 : x0 + m], cv2.COLOR_BGR2GRAY
                )
            if cara_carnet is None or cara_selfie is None:
                return 0.0
            a = _normalizar_cara(cara_carnet)
            b = _normalizar_cara(cara_selfie)
            return float(_similitud_caras(a, b))
        except Exception as error:
            logger.info("face-match falló: %s", error)
            return 0.0

class ComparadorRostrosFijo:

    def __init__(self, score: float = 0.9) -> None:
        self.score = float(score)

    def comparar(self, carnet_jpeg: bytes, selfie_jpeg: bytes) -> float:
        if not carnet_jpeg or not selfie_jpeg:
            return 0.0
        return self.score
