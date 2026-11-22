

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

DOC_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "privacy_policy": [
        re.compile(r"pol[ií]tica\s+de\s+privacidad", re.I),
        re.compile(r"privacy\s*policy", re.I),
        re.compile(r"protecci[oó]n\s+de\s+datos", re.I),
        re.compile(r"/privacy\b|/privacidad\b|politica-de-privacidad", re.I),
    ],
    "terms": [
        re.compile(r"t[eé]rminos\s+y\s+condiciones", re.I),
        re.compile(r"terms\s*(and|&)\s*conditions", re.I),
        re.compile(r"terms\s+of\s+service", re.I),
        re.compile(r"condiciones\s+de\s+uso", re.I),
        re.compile(r"condiciones\s+(est[aá]ndar\s+)?de\s+venta", re.I),
    ],
    "sla": [re.compile(r"\bSLA\b"), re.compile(r"nivel(?:es)?\s+de\s+servicio", re.I)],
    "dpa": [
        re.compile(r"\bDPA\b"),
        re.compile(r"acuerdo\s+de\s+tratamiento\s+de\s+datos", re.I),

        re.compile(r"tratamiento\s+de\s+(datos\s+personales|sus\s+datos)", re.I),
        re.compile(r"procesa(?:miento|mos)\s+de?\s*datos\s+personales", re.I),
        re.compile(
            r"how\s+we\s+(collect|use|process|handle)\s+(your\s+)?(personal\s+)?data",
            re.I,
        ),
        re.compile(r"personal\s+data\s+we\s+collect", re.I),
    ],
    "service_clauses": [
        re.compile(r"cl[aá]usulas?\s+de\s+servicio", re.I),
        re.compile(r"condiciones\s+del?\s+servicio", re.I),
        re.compile(r"condiciones\s+(est[aá]ndar\s+)?de\s+venta", re.I),
        re.compile(r"terms\s+of\s+(sale|service)", re.I),
    ],
}
LEY_21719 = re.compile(r"21\.?\s*719|ley\s+21\.?719", re.I)
COOKIE_NOTICE = re.compile(r"cookie|cookies|consentimiento", re.I)
CONTACT_DATA = re.compile(
    r"delegad[oa]\s+de\s+datos|dpo|data\s+protection\s+officer|"
    r"contacto.*datos|ARCO|habeas\s+data|"
    r"ejercer\s+(sus\s+)?derechos|privacidad@|privacy@",
    re.I,
)

_MIXED_SUBRESOURCE = re.compile(
    r"""<(?:script|img|iframe|source|embed|object|video|audio)\b[^>]*\b(?:src)\s*=\s*["']http://"""
    r"""|<(?:link)\b[^>]*\bhref\s*=\s*["']http://"""
    r"""|url\(\s*['"]?http://""",
    re.I,
)

_RUTAS_LEGALES = (
    "/privacy",
    "/privacidad",
    "/politica-de-privacidad",
    "/politica-privacidad",
    "/terms",
    "/terminos",
    "/terminos-y-condiciones",
    "/cookies",
    "/cookie-policy",
    "/aviso-legal",
)

_DOC_A_CON: dict[str, str] = {
    "privacy_policy": "con_privacy",
    "ley_21719": "con_ley_21719",
    "terms": "con_tyc",
    "sla": "con_sla",
    "dpa": "con_dpa",
    "service_clauses": "con_clausulas",
    "data_contact": "con_contacto_datos",
    "cookies_notice": "con_cookies_notice",
}

def _normalize_url(url: str) -> str:
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u.rstrip("/")

def _urls_candidatas(url_sitio: str) -> list[str]:

    start = _normalize_url(url_sitio)
    out = [start]
    parsed = urlparse(start)
    host = (parsed.netloc or "").strip().lower()
    if not host:
        return out
    if host.startswith("www."):
        alt = parsed._replace(netloc=host[4:]).geturl()
    else:
        alt = parsed._replace(netloc="www." + host).geturl()
    if alt.rstrip("/") not in {start, start + "/"}:
        out.append(alt.rstrip("/"))
    return out

def ruta_mostrar(url: str | None, *, home_url: str = "") -> str | None:

    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    if raw.startswith("link:"):
        href = raw[5:].strip()
        if not href:
            return None
        if href.startswith("http://") or href.startswith("https://"):
            path = urlparse(href).path or "/"
        elif href.startswith("/"):
            path = href.split("?", 1)[0].split("#", 1)[0]
        else:
            path = "/" + href.split("?", 1)[0].split("#", 1)[0]
        path = path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path or None
    if raw.startswith("http://") or raw.startswith("https://"):
        path = urlparse(raw).path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path or "/"
    if raw.startswith("/"):
        path = raw.split("?", 1)[0].split("#", 1)[0]
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return path or "/"
    if home_url:
        try:
            origen = f"{urlparse(home_url).scheme}://{urlparse(home_url).netloc}"
            return ruta_mostrar(origen.rstrip("/") + "/" + raw.lstrip("/"), home_url=home_url)
        except Exception:
            return None
    return None

def rastrear_sitio(url_sitio: str, *, tiempo_espera: float = 1.5) -> dict[str, Any]:

    vacio = {
        "paginas_escaneadas": 0,
        "pistas_puntaje": {},
        "hallazgos_count": 0,
        "info_headers": {},
        "rutas_evidencia": {},
    }
    if BeautifulSoup is None:
        return vacio

    page_texts: dict[str, str] = {}
    page_html: dict[str, str] = {}
    headers_info: dict[str, Any] = {}
    rr = None
    try:
        with httpx.Client(
            timeout=httpx.Timeout(
                tiempo_espera, connect=min(2.0, max(0.8, tiempo_espera))
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "ServiChileEvaluador/1.0",

                "Cache-Control": "no-cache, no-store",
                "Pragma": "no-cache",
            },
        ) as cliente:
            for candidato in _urls_candidatas(url_sitio):
                try:
                    cand = cliente.get(candidato)
                except Exception:
                    continue
                if cand.status_code < 400:
                    rr = cand
                    break
            if rr is None or rr.status_code >= 400:
                return vacio

            headers_info = {
                "url": str(rr.url),
                "status": rr.status_code,
                "headers": {k.lower(): v for k, v in rr.headers.items()},
                "is_https": str(rr.url).startswith("https"),
                "set_cookie": (
                    rr.headers.get_list("set-cookie")
                    if hasattr(rr.headers, "get_list")
                    else (
                        [rr.headers["set-cookie"]]
                        if "set-cookie" in rr.headers
                        else []
                    )
                ),
            }
            _incorporar_html(rr, page_texts, page_html)
            _sondear_rutas_legales(cliente, str(rr.url), page_texts, page_html)
    except Exception:
        return vacio

    if not page_texts:
        return vacio

    headers_info["mixed_content_hits"] = _contar_mixed_content(
        page_html, https=bool(headers_info.get("is_https"))
    )
    hallazgos = _analizar(page_texts, page_html)
    pistas = _pistas_puntaje(hallazgos, headers_info, page_texts)
    home = str(headers_info.get("url") or "")
    rutas = _rutas_evidencia_con(hallazgos, home_url=home)

    if (
        float(pistas.get("con_clausulas") or 0) > 0
        and "con_clausulas" not in rutas
        and "con_tyc" in rutas
    ):
        rutas["con_clausulas"] = rutas["con_tyc"]
    return {
        "paginas_escaneadas": len([u for u in page_texts if not u.startswith("link:")]),
        "pistas_puntaje": pistas,
        "hallazgos_count": sum(1 for f in hallazgos if f.get("found")),
        "info_headers": {
            k: v
            for k, v in headers_info.items()
            if k not in {"headers", "set_cookie"}
        },
        "rutas_evidencia": rutas,
    }

def _incorporar_html(
    response: httpx.Response,
    page_texts: dict[str, str],
    page_html: dict[str, str],
) -> None:
    ct = response.headers.get("content-type", "")
    if "text/html" not in ct and "application/xhtml" not in ct:
        return
    html = response.text
    url = str(response.url)
    page_html[url] = html
    soup = BeautifulSoup(html, "lxml")
    page_texts[url] = soup.get_text(" ", strip=True)
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").lower()
        label = f"{a.get_text(' ', strip=True)} {href}".lower()
        page_texts[f"link:{href}"] = f"{label} {href}"[:500]

def _sondear_rutas_legales(
    cliente: httpx.Client,
    home_url: str,
    page_texts: dict[str, str],
    page_html: dict[str, str],
) -> None:

    parsed = urlparse(home_url)
    origen = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    vistos = {urlparse(u).path.rstrip("/") for u in page_html}
    for ruta in _RUTAS_LEGALES:
        if ruta.rstrip("/") in vistos:
            continue
        try:
            resp = cliente.get(origen + ruta)
        except Exception:
            continue
        if resp.status_code >= 400:
            continue

        cuerpo = (resp.text or "")[:4000].lower()
        if "page not found" in cuerpo or "página no encontrada" in cuerpo:
            continue
        _incorporar_html(resp, page_texts, page_html)
        vistos.add(ruta.rstrip("/"))
        if len([u for u in page_html if not u.startswith("link:")]) >= 4:
            break

def _analizar(page_texts: dict[str, str], page_html: dict[str, str]) -> list[dict]:
    hallazgos: list[dict] = []
    for doc_type, patterns in DOC_PATTERNS.items():
        best_conf = 0.0
        found_url = None
        for url, text in page_texts.items():
            blob = f"{url} {text[:8000]}"
            hits = sum(1 for p in patterns if p.search(blob))
            if hits == 0:
                continue
            conf = min(1.0, 0.35 * hits + (0.25 if any(p.search(url) for p in patterns) else 0))
            if conf > best_conf:
                best_conf = conf
                found_url = url

        min_conf = 0.35
        hallazgos.append(
            {"doc_type": doc_type, "found": best_conf >= min_conf, "url": found_url}
        )

    ley_url = _primera_url_match(page_texts, page_html, LEY_21719, html_limit=0)
    hallazgos.append(
        {"doc_type": "ley_21719", "found": ley_url is not None, "url": ley_url}
    )
    cookie_url = _primera_url_match(
        page_texts, page_html, COOKIE_NOTICE, text_limit=3000, html_limit=2000
    )
    hallazgos.append(
        {
            "doc_type": "cookies_notice",
            "found": cookie_url is not None,
            "url": cookie_url,
        }
    )
    contact_url = _primera_url_match(page_texts, page_html, CONTACT_DATA, html_limit=0)
    hallazgos.append(
        {
            "doc_type": "data_contact",
            "found": contact_url is not None,
            "url": contact_url,
        }
    )
    return hallazgos

def _primera_url_match(
    page_texts: dict[str, str],
    page_html: dict[str, str],
    patron: re.Pattern[str],
    *,
    text_limit: int | None = None,
    html_limit: int = 0,
) -> str | None:

    candidatas: list[tuple[int, str]] = []
    for url, text in page_texts.items():
        blob = text if text_limit is None else text[:text_limit]
        if patron.search(blob) or patron.search(url):
            prio = 0 if not url.startswith("link:") else 1
            candidatas.append((prio, url))
    if html_limit > 0:
        for url, html in page_html.items():
            if patron.search((html or "")[:html_limit]):
                prio = 0 if not url.startswith("link:") else 1
                candidatas.append((prio, url))
    if not candidatas:
        return None
    candidatas.sort(key=lambda x: x[0])
    return candidatas[0][1]

def _rutas_evidencia_con(hallazgos: list[dict], *, home_url: str) -> dict[str, str]:

    out: dict[str, str] = {}
    for h in hallazgos:
        if not h.get("found"):
            continue
        pid = _DOC_A_CON.get(str(h.get("doc_type") or ""))
        if not pid:
            continue
        ruta = ruta_mostrar(h.get("url"), home_url=home_url)
        if ruta:
            out[pid] = ruta
    return out

def _contar_mixed_content(page_html: dict[str, str], *, https: bool) -> int:
    if not https:
        return 0
    hits = 0
    for html in page_html.values():
        hits += len(_MIXED_SUBRESOURCE.findall(html or ""))
    return hits

def _pistas_puntaje(
    hallazgos: list[dict], headers_info: dict[str, Any], page_texts: dict[str, str]
) -> dict[str, float]:
    by_type = {f["doc_type"]: f for f in hallazgos}
    headers = (headers_info or {}).get("headers") or {}

    def hdr(name: str) -> str:
        return str(headers.get(name, "")).lower()

    cookies = headers_info.get("set_cookie") or []
    cookie_str = " ".join(cookies).lower()
    found = lambda t: bool(by_type.get(t, {}).get("found"))

    mixed_hits = int(headers_info.get("mixed_content_hits") or 0)
    if not headers_info.get("is_https"):
        mixed_score = 40.0
    elif mixed_hits <= 0:
        mixed_score = 100.0
    else:
        mixed_score = max(0.0, 100.0 - min(100.0, float(mixed_hits) * 40.0))

    return {
        "cyb_https": 100.0 if headers_info.get("is_https") else 10.0,
        "cyb_hsts": 100.0 if "strict-transport-security" in headers else 0.0,
        "cyb_csp": 100.0 if "content-security-policy" in headers else 0.0,
        "cyb_xfo": 100.0
        if "x-frame-options" in headers or "frame-ancestors" in hdr("content-security-policy")
        else 0.0,
        "cyb_xcto": 100.0 if "nosniff" in hdr("x-content-type-options") else 0.0,
        "cyb_referrer": 100.0 if "referrer-policy" in headers else 0.0,
        "cyb_cookies": 80.0
        if cookies and ("secure" in cookie_str or "httponly" in cookie_str)
        else (40.0 if not cookies else 20.0),
        "cyb_mixed": mixed_score,
        "con_privacy": 100.0 if found("privacy_policy") else 0.0,
        "con_ley_21719": 100.0 if found("ley_21719") else 0.0,
        "con_tyc": 100.0 if found("terms") else 0.0,
        "con_sla": 100.0 if found("sla") else 0.0,
        "con_dpa": 100.0 if found("dpa") else 0.0,
        "con_clausulas": 100.0 if found("service_clauses") else (50.0 if found("terms") else 0.0),
        "con_contacto_datos": 100.0 if found("data_contact") else 0.0,
        "con_cookies_notice": 100.0 if found("cookies_notice") else 0.0,
        "dig_website": 100.0 if page_texts else 0.0,
    }

def dominio_de_url(sitio: str | None) -> str | None:
    if not sitio or not str(sitio).strip():
        return None
    raw = str(sitio).strip()
    if not raw.startswith("http"):
        raw = "https://" + raw
    host = (urlparse(raw).netloc or "").removeprefix("www.").lower()
    return host or None
