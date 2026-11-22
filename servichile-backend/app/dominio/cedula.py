

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.dominio.rut import RutInvalido, normalizar_rut

CEDULA_MAX_BYTES = 8 * 1024 * 1024
CEDULA_MAX_LADO_DEFAULT = 1600
CEDULA_JPEG_QUALITY_DEFAULT = 82
CEDULA_RETENCION_DIAS_DEFAULT = 180
CEDULA_CONTENT_TYPE = "image/jpeg"
UMBRAL_ACEPTACION = 70

_OBLIGATORIAS = frozenset({"calidad-imagen", "formato-chile", "rut-valido", "face-match"})
UMBRAL_FACE_DEFAULT = 0.52

_MESES = {
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "setiembre": 9,
    "sep": 9,
    "sept": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}

_NOMBRE_STOP = frozenset(
    {
        "chile",
        "chilena",
        "chileno",
        "republica",
        "servicio",
        "registro",
        "civil",
        "identificacion",
        "identidad",
        "cedula",
        "carnet",
        "nacionalidad",
        "sexo",
        "fecha",
        "nacimiento",
        "emision",
        "vencimiento",
        "numero",
        "documento",
        "firma",
        "titular",
        "run",
        "rut",
        "apellidos",
        "nombres",
        "apellido",
        "nombre",
    }
)

@dataclass(frozen=True)
class MetaCedula:
    ruta_relativa: str
    sha256: str
    bytes_: int
    ancho: int
    alto: int
    content_type: str = CEDULA_CONTENT_TYPE

@dataclass(frozen=True)
class ResultadoCedula:
    aceptado: bool
    score: int
    rut: str | None
    nombre_ocr: str | None
    senales: tuple[str, ...]
    motivo: str
    texto_compacto_len: int = 0
    face_score: float | None = None

def retener_hasta(
    desde: datetime | None = None, *, dias: int = CEDULA_RETENCION_DIAS_DEFAULT
) -> datetime:
    base = desde or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(days=max(1, int(dias)))

def _compact(texto: str) -> str:
    return re.sub("[^a-z0-9]", "", (texto or "").lower())

def _sin_acentos(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

def _extraer_ruts(texto: str) -> list[str]:
    candidatos: list[str] = []

    patrones = (
        r"(?:R\.?\s*U\.?\s*N\.?|RUN|RUT)\s*[:#]?\s*([0-9]{1,2}\.?[0-9]{3}\.?[0-9]{3}\s*-?\s*[0-9Kk])",
        r"(?<![0-9])([0-9]{1,2}\.[0-9]{3}\.[0-9]{3}\s*-\s*[0-9Kk])(?![0-9])",
        r"(?<![0-9])([0-9]{7,8}\s*-\s*[0-9Kk])(?![0-9])",
    )
    vistos: set[str] = set()
    for pat in patrones:
        for m in re.finditer(pat, texto or "", re.I):
            crudo = re.sub(r"[\s.]", "", m.group(1)).upper()
            if "-" not in crudo and len(crudo) >= 2:
                crudo = crudo[:-1] + "-" + crudo[-1]
            try:
                rut = normalizar_rut(crudo)
            except RutInvalido:
                continue
            if rut not in vistos:
                vistos.add(rut)
                candidatos.append(rut)
    return candidatos

def _extraer_numero_documento(texto: str) -> str | None:
    m = re.search(r"\b([A-Z][0-9A-Z]{1,2}\.\d{3}\.\d{3})\b", texto or "", re.I)
    return m.group(1).upper() if m else None

def _linea_nombre(linea: str) -> bool:
    limpia = re.sub(r"[^A-ZÁÉÍÓÚÑa-záéíóúñ\s]", "", linea or "").strip()
    if len(limpia) < 3:
        return False
    tokens = [t for t in limpia.split() if t]
    if not tokens or len(tokens) > 4:
        return False
    for t in tokens:
        base = _sin_acentos(t).lower()
        if base in _NOMBRE_STOP or len(base) < 2:
            return False
        if not re.fullmatch(r"[A-ZÁÉÍÓÚÑa-záéíóúñ]+", t):
            return False

    mayus = sum(1 for t in tokens if t == t.upper())
    return mayus >= max(1, len(tokens) - 1)

def _extraer_nombre(texto: str) -> str | None:
    m = re.search(
        r"(?:apellidos?\s*(?:y|/)?\s*nombres?|nombres?\s*(?:y|/)?\s*apellidos?)\s*[:#]?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,80})",
        texto or "",
        re.I,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()

    lineas = [ln.strip() for ln in (texto or "").splitlines()]
    bloque: list[str] = []
    for ln in lineas:
        baja = _sin_acentos(ln).lower().strip(" :.")
        if baja in {"apellidos", "apellido", "nombres", "nombre"}:
            continue
        if _linea_nombre(ln):
            bloque.append(re.sub(r"\s+", " ", ln))
            if len(bloque) >= 4:
                break
        elif bloque and not baja:
            continue
        elif bloque:

            if any(
                k in baja
                for k in (
                    "nacionalidad",
                    "sexo",
                    "fecha",
                    "numero",
                    "documento",
                    "firma",
                    "run",
                    "chile",
                )
            ):
                break
    if len(bloque) >= 2:
        return " ".join(bloque)
    return None

def _parse_fecha(texto: str) -> date | None:
    m = re.search(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        texto or "",
    )
    if m:
        d, mo, y = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        try:
            return date(y, mo, d)
        except ValueError:
            return None

    m = re.search(
        r"(\d{1,2})\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s*(?:de\s+)?(\d{4})",
        texto or "",
        re.I,
    )
    if not m:
        return None
    mes = _MESES.get(_sin_acentos(m.group(2)).lower())
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None

def _todas_fechas(texto: str) -> list[date]:
    out: list[date] = []
    for m in re.finditer(
        r"(\d{1,2})\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s*(?:de\s+)?(\d{4})",
        texto or "",
        re.I,
    ):
        mes = _MESES.get(_sin_acentos(m.group(2)).lower())
        if not mes:
            continue
        try:
            out.append(date(int(m.group(3)), mes, int(m.group(1))))
        except ValueError:
            continue
    return out

def _tokens_nombre(nombre: str) -> set[str]:
    limpio = re.sub(r"[^a-záéíóúñ\s]", " ", _sin_acentos(nombre).lower())
    return {t for t in limpio.split() if len(t) >= 2}

def _nombre_coincide(nombre_ocr: str | None, nombre_cuenta: str | None) -> bool:
    if not nombre_ocr or not nombre_cuenta:
        return False
    a = _tokens_nombre(nombre_ocr)
    b = _tokens_nombre(nombre_cuenta)
    if not a or not b:
        return False
    inter = a & b
    return len(inter) >= min(2, len(b))

def validar_cedula(
    *,
    texto_ocr: str,
    ancho: int,
    alto: int,
    bytes_: int,
    rut_perfil: str | None = None,
    nombre_perfil: str | None = None,
    rut_perfil_verificado: bool = False,
    face_score: float | None = None,
    umbral_face: float = UMBRAL_FACE_DEFAULT,
) -> ResultadoCedula:
    senales: list[str] = []
    faltantes: list[str] = []
    score = 0

    if ancho >= 400 and alto >= 240 and bytes_ >= 3_000:
        score += 15
        senales.append("calidad-imagen")
    else:
        faltantes.append("foto nítida del carnet (mín. ~400×240)")

    if alto > 0:
        ratio = ancho / alto
        if 1.25 <= ratio <= 2.05:
            score += 10
            senales.append("proporcion-carnet")
        else:
            faltantes.append("encuadre tipo carnet (horizontal)")

    compact = _compact(texto_ocr)
    es_chile = (
        "republicadechile" in compact
        or "registrocivil" in compact
        or "ceduladeidentidad" in compact
        or "carnetdeidentidad" in compact
        or ("chile" in compact and "identidad" in compact)
        or ("chile" in compact and ("run" in compact or "rut" in compact))
    )
    if es_chile:
        score += 20
        senales.append("formato-chile")
    else:
        faltantes.append("texto de cédula chilena / Registro Civil")

    if "nacionalidad" in compact or "chilena" in compact or "chileno" in compact:
        score += 5
        senales.append("nacionalidad")

    if "fechanacimiento" in compact or "nacimiento" in compact or "nachmento" in compact:
        score += 5
        senales.append("fecha-nacimiento")

    if "vencimiento" in compact or "fechadevencimiento" in compact:
        score += 5
        senales.append("fecha-vencimiento")

    if _extraer_numero_documento(texto_ocr):
        score += 5
        senales.append("numero-documento")

    ruts = _extraer_ruts(texto_ocr)
    rut = ruts[0] if ruts else None
    if rut:
        score += 25
        senales.append("rut-valido")
    else:
        faltantes.append("R.U.N. legible con dígito verificador válido")

    nombre_ocr = _extraer_nombre(texto_ocr)
    if nombre_ocr:
        score += 5
        senales.append("nombre-ocr")

    if rut and rut_perfil_verificado and rut_perfil:
        if rut == rut_perfil:
            score += 15
            senales.append("rut-coincide-perfil")
        else:
            faltantes.append("el RUT de la foto no coincide con el RUT verificado de la cuenta")
            score = min(score, 40)
    elif rut and rut_perfil and not rut_perfil_verificado:
        if rut == rut_perfil:
            score += 10
            senales.append("rut-coincide-perfil")

    if _nombre_coincide(nombre_ocr, nombre_perfil):
        score += 10
        senales.append("nombre-coincide")

    fechas = _todas_fechas(texto_ocr)
    venc = None

    if "vencimiento" in (texto_ocr or "").lower():
        idx = (texto_ocr or "").lower().rfind("venc")
        if idx >= 0:
            bloque = _todas_fechas((texto_ocr or "")[idx : idx + 80])
            if bloque:
                venc = max(bloque)
    if venc is None and fechas:

        futuras = [f for f in fechas if f >= date.today()]
        venc = max(futuras) if futuras else max(fechas)
    if venc and venc < date.today():
        faltantes.append("cédula vencida")
        score = min(score, 55)
    elif venc and venc >= date.today():
        score += 5
        senales.append("vigente")

    if face_score is None:
        faltantes.append("selfie biométrica previa (complete la verificación facial primero)")
    elif float(face_score) >= float(umbral_face):
        score += 15
        senales.append("face-match")
    else:
        faltantes.append(
            f"el rostro del carnet no coincide con su selfie ({float(face_score):.0%} < {float(umbral_face):.0%})"
        )
        score = min(score, 50)

    score = min(100, score)
    tiene_obligatorias = _OBLIGATORIAS.issubset(senales)
    conflicto_rut = (
        rut is not None
        and rut_perfil_verificado
        and rut_perfil
        and rut != rut_perfil
    )
    face_ok = face_score is not None and float(face_score) >= float(umbral_face)
    aceptado = (
        score >= UMBRAL_ACEPTACION
        and tiene_obligatorias
        and rut is not None
        and not conflicto_rut
        and face_ok
        and "cédula vencida" not in faltantes
    )

    if not aceptado:
        if conflicto_rut:
            motivo = (
                f"El RUT leído ({rut}) no coincide con el RUT verificado de su cuenta "
                f"({rut_perfil})."
            )
        elif face_score is not None and not face_ok:
            motivo = (
                f"El rostro del carnet no coincide con su selfie guardada "
                f"({float(face_score):.0%}). Reencuadre el frente y reintente."
            )
        elif faltantes:
            motivo = (
                f"No se pudo validar la cédula ({score}/100). Falta: "
                f"{', '.join(faltantes[:4])}."
            )
        else:
            motivo = (
                f"No alcanza el umbral de validación ({score}/100). "
                "Use una foto frontal nítida del carnet chileno."
            )
    else:
        motivo = (
            f"Cédula válida. RUT {rut} ({score}/100). "
            f"Face-match {float(face_score):.0%}."
        )

    return ResultadoCedula(
        aceptado=aceptado,
        score=score,
        rut=rut if aceptado or rut else rut,
        nombre_ocr=nombre_ocr,
        senales=tuple(senales),
        motivo=motivo,
        texto_compacto_len=len(compact),
        face_score=None if face_score is None else round(float(face_score), 4),
    )
