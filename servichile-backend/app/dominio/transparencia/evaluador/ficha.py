

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

STOPWORDS = {
    "ltda",
    "limitada",
    "spa",
    "sa",
    "s.a",
    "s.a.",
    "eirl",
    "chile",
    "para",
    "de",
    "la",
    "el",
    "los",
    "las",
    "y",
    "e",
    "del",
    "informacion",
    "información",
    "gestion",
    "gestión",
    "tecnologia",
    "tecnología",
    "empresa",
    "servicios",
    "servicio",
    "service",
    "services",
    "group",
    "grupo",
    "company",
    "comercial",
}

FOREIGN_MARKERS = (
    "colombia",
    "méxico",
    "mexico",
    "argentina",
    "perú",
    "peru",
    "españa",
    "spain",
    "usa",
    "united states",
    ".com.co",
    ".com.mx",
    ".com.ar",
    ".com.br",
    ".com.pe",
)

CHILE_HINTS = (
    "chile",
    "santiago",
    "región metropolitana",
    "region metropolitana",
    "valparaíso",
    "valparaiso",
    "biobío",
    "biobio",
    "araucanía",
    "araucania",
    "los lagos",
    "antofagasta",
    "coquimbo",
    "ñuble",
    "nuble",
    "maule",
    "ohiggins",
    "o'higgins",
)

@dataclass
class EvaluacionFicha:
    confiable: bool
    confianza: float
    puntaje_coincidencia: int
    razones: list[str] = field(default_factory=list)
    nombre_lugar: str | None = None
    direccion_lugar: str | None = None
    sitio_lugar: str | None = None
    coincidencia_nombre: bool = False
    coincidencia_dominio: bool = False
    coincidencia_chile: bool = False
    extranjero: bool = False
    colision_marca: bool = False

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)

def _plegar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def _host(url: str | None) -> str:
    if not url:
        return ""
    u = url.lower().strip()
    if not u.startswith("http"):
        u = "https://" + u
    host = (urlparse(u).netloc or "").removeprefix("www.")
    return host

def raiz_dominio(dominio: str | None) -> str | None:
    host = _host(dominio) if dominio and "://" in (dominio or "") else (dominio or "").lower()
    host = host.removeprefix("www.").split("/")[0]
    if not host:
        return None
    stem = host.split(".")[0]
    return stem if len(stem) >= 3 else None

def tokens_marca(nombre_empresa: str | None, dominio: str | None = None) -> list[str]:

    tokens: list[str] = []
    stem = raiz_dominio(dominio)
    if stem and stem not in STOPWORDS:
        tokens.append(stem)

    raw = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", nombre_empresa or "")
    for t in raw:
        folded = _plegar(t)
        min_len = 3 if stem and folded == stem else 4
        if len(folded) < min_len or folded in STOPWORDS:
            continue
        if folded not in tokens:
            tokens.append(folded)
    return tokens

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]

def _similar_pero_distinto(a: str, b: str) -> bool:

    if not a or not b or a == b:
        return False
    if a in b or b in a:
        return False
    if abs(len(a) - len(b)) > 4:
        return False
    if min(len(a), len(b)) < 5:
        return False
    dist = _levenshtein(a, b)
    ratio = dist / max(len(a), len(b))
    return 0.15 <= ratio <= 0.45

def _tokens_nombre_lugar(pname: str) -> list[str]:
    return [
        t
        for t in re.findall(r"[a-z0-9]+", _plegar(pname))
        if len(t) >= 3 and t not in STOPWORDS
    ]

def afiliacion_nombre(tokens: list[str], place_name: str) -> tuple[bool, str]:

    pname = _plegar(place_name)
    if not tokens or not pname:
        return False, "sin nombre Places o sin fragmentos"
    ptoks = set(_tokens_nombre_lugar(pname))
    for tok in tokens:
        if tok in ptoks:
            return True, f"fragmento '{tok}' en nombre Places"
        if re.search(rf"(^|[^a-z0-9]){re.escape(tok)}([^a-z0-9]|$)", pname):
            return True, f"fragmento '{tok}' como palabra en nombre Places"
    return False, f"ningún fragmento {tokens} en '{place_name}'"

def detectar_colision_marca(tokens: list[str], place_name: str) -> bool:
    ptoks = _tokens_nombre_lugar(place_name)
    for tok in tokens:
        for pt in ptoks:
            if _similar_pero_distinto(tok, pt):
                return True
    return False

def dominios_coinciden(dominio_empresa: str, website_uri: str | None) -> bool:

    want = _host(dominio_empresa) or (dominio_empresa or "").lower().removeprefix("www.")
    got = _host(website_uri)
    if not want or not got:
        return False
    want = want.split("/")[0]
    return got == want or got.endswith("." + want)

def puntuar_candidato_lugar(
    place: dict[str, Any],
    *,
    nombre_empresa: str | None,
    dominio: str,
    comuna: str | None = None,
    ciudad: str | None = None,
) -> EvaluacionFicha:

    addr = (place.get("formattedAddress") or "").lower()
    web = (place.get("websiteUri") or "").lower()
    pname_raw = (place.get("displayName") or {}).get("text") or ""
    pname = _plegar(pname_raw)
    web_host = _host(place.get("websiteUri"))
    tokens = tokens_marca(nombre_empresa, dominio)

    razones: list[str] = []
    score = 0

    coincidencia_dominio = dominios_coinciden(dominio, place.get("websiteUri"))
    if coincidencia_dominio:
        score += 80
        razones.append(f"dominio coincide ({web_host})")
    elif web_host:
        razones.append(f"dominio no coincide (web={web_host})")
        score -= 25
    else:
        razones.append("ficha sin websiteUri")

    coincidencia_nombre, razon_nombre = afiliacion_nombre(tokens, pname_raw)
    if coincidencia_nombre:
        score += 70
        razones.append(razon_nombre)
    elif tokens:
        score -= 40
        razones.append(razon_nombre)
    else:
        razones.append("sin tokens de marca para validar nombre")

    colision_marca = False
    if tokens and not coincidencia_nombre and not coincidencia_dominio:
        colision_marca = detectar_colision_marca(tokens, pname_raw)
        if colision_marca:
            score -= 60
            razones.append("posible colisión de marca parecida (FP)")

    coincidencia_chile = any(h in addr for h in CHILE_HINTS) or (
        web_host.endswith(".cl") if web_host else False
    )
    if coincidencia_chile:
        score += 25
        razones.append("señales de ubicación Chile")
    else:
        score -= 30
        razones.append("sin señales claras de Chile en dirección/web")

    extranjero = any(m in addr or m in web for m in FOREIGN_MARKERS)
    if extranjero:
        score -= 100
        razones.append("posible ubicación/dominio extranjero")

    if comuna and _plegar(comuna) in _plegar(addr):
        score += 10
        razones.append(f"comuna '{comuna}' en dirección")
    if ciudad and _plegar(ciudad) in _plegar(addr):
        score += 5
        razones.append(f"ciudad '{ciudad}' en dirección")

    confianza = max(0.0, min(1.0, (score + 100) / 290.0))

    confiable = True
    fallas_duras: list[str] = []

    if extranjero:
        confiable = False
        fallas_duras.append("ficha extranjera")
    if colision_marca and not coincidencia_dominio:
        confiable = False
        fallas_duras.append("colisión de marca sin dominio")
    if not coincidencia_chile and not coincidencia_dominio:
        confiable = False
        fallas_duras.append("sin evidencia Chile")

    identidad_ok = False
    if coincidencia_dominio:
        identidad_ok = True
        razones.append("identidad por dominio (reduce FN)")
    elif coincidencia_nombre and coincidencia_chile:
        identidad_ok = True
        razones.append("identidad por nombre+Chile")
    else:
        confiable = False
        fallas_duras.append("sin identidad fuerte (ni dominio ni nombre+Chile)")

    if identidad_ok and coincidencia_dominio:
        if score < 55:
            confiable = False
            fallas_duras.append(f"puntaje_coincidencia insuficiente con dominio ({score}<55)")
        if confianza < 0.40:
            confiable = False
            fallas_duras.append(f"confianza baja ({confianza:.2f}<0.40)")
    elif identidad_ok:
        if score < 80:
            confiable = False
            fallas_duras.append(f"puntaje_coincidencia insuficiente sin dominio ({score}<80)")
        if confianza < 0.55:
            confiable = False
            fallas_duras.append(f"confianza baja ({confianza:.2f}<0.55)")

    if not confiable:
        razones.append("NO CONFIABLE: " + "; ".join(fallas_duras))
    else:
        razones.append("CONFIABLE para scoring físico/reputacional")

    return EvaluacionFicha(
        confiable=confiable,
        confianza=round(confianza, 3),
        puntaje_coincidencia=score,
        razones=razones,
        nombre_lugar=pname_raw or None,
        direccion_lugar=place.get("formattedAddress"),
        sitio_lugar=place.get("websiteUri"),
        coincidencia_nombre=coincidencia_nombre,
        coincidencia_dominio=coincidencia_dominio,
        coincidencia_chile=coincidencia_chile,
        extranjero=extranjero,
        colision_marca=colision_marca,
    )

def elegir_lugar_confiable(
    places: list[dict[str, Any]],
    *,
    nombre_empresa: str | None,
    dominio: str,
    comuna: str | None = None,
    ciudad: str | None = None,
) -> tuple[dict[str, Any] | None, EvaluacionFicha]:

    if not places:
        vacio = EvaluacionFicha(
            confiable=False,
            confianza=0.0,
            puntaje_coincidencia=0,
            razones=["sin candidatos Places"],
        )
        return None, vacio

    ranked: list[tuple[EvaluacionFicha, dict[str, Any]]] = []
    for p in places:
        evaluacion = puntuar_candidato_lugar(
            p,
            nombre_empresa=nombre_empresa,
            dominio=dominio,
            comuna=comuna,
            ciudad=ciudad,
        )
        ranked.append((evaluacion, p))
    ranked.sort(
        key=lambda x: (
            x[0].confiable,
            x[0].coincidencia_dominio,
            bool(x[1].get("websiteUri")),
            x[0].coincidencia_nombre,
            int(x[1].get("userRatingCount") or 0),
            bool(x[1].get("regularOpeningHours")),
            x[0].puntaje_coincidencia,
            x[0].confianza,
        ),
        reverse=True,
    )
    mejor_eval, mejor_lugar = ranked[0]
    if not mejor_eval.confiable:
        return None, mejor_eval
    return mejor_lugar, mejor_eval

FISICA_PARAM_IDS = (
    "fis_places_exists",
    "fis_rating",
    "fis_reviews",
    "fis_address",
    "fis_phone",
    "fis_hours",
)
