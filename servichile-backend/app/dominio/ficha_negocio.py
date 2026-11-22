

from __future__ import annotations

import re

CTA_POR_CATEGORIA = {
    "tecnologia": "Ver ficha de transparencia",
    "industria": "Evaluar proveedor",
    "construccion": "Evaluar contratista",
    "servicios-profesionales": "Ver transparencia",
    "logistica": "Validar operador logístico",
}

IMAGEN_POR_CATEGORIA = {
    "tecnologia": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=480&h=300&q=55",
    "industria": "https://images.unsplash.com/photo-1504328345606-18bbc8c9d7d1?auto=format&fit=crop&w=480&h=300&q=55",
    "construccion": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=480&h=300&q=55",
    "servicios-profesionales": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=480&h=300&q=55",
    "logistica": "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=480&h=300&q=55",
}

_ESQUEMAS_BLOQUEADOS = ("javascript:", "data:", "vbscript:", "file:", "blob:")
_URL_MAX = 500

def cta_texto(categoria: str) -> str:
    return CTA_POR_CATEGORIA.get(categoria, "Ver ficha")

def imagen_por_defecto(categoria: str) -> str:
    return IMAGEN_POR_CATEGORIA.get(categoria, IMAGEN_POR_CATEGORIA["tecnologia"])

def logo_texto(nombre: str) -> str:
    partes = re.sub("[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\\s]", " ", nombre or "").split()
    partes = [p for p in partes if p]
    if not partes:
        return "S"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()

def normalizar_url_recurso(valor: str | None, *, max_len: int = _URL_MAX) -> str | None:

    if valor is None:
        return None
    url = valor.strip()
    if not url:
        return None
    if len(url) > max_len:
        raise ValueError(f"La URL no puede superar {max_len} caracteres")
    if any(c.isspace() for c in url):
        raise ValueError("La URL no puede contener espacios")

    bajo = url.lower()
    for pref in _ESQUEMAS_BLOQUEADOS:
        if bajo.startswith(pref):
            raise ValueError("Esquema de URL no permitido")

    if bajo.startswith("http://"):
        url = "https://" + url[7:]
        bajo = url.lower()
    elif not bajo.startswith("https://"):
        raise ValueError("La URL debe comenzar con https://")

    host = url[8:].split("/", 1)[0]
    if not host or host.startswith(".") or host.endswith("."):
        raise ValueError("La URL no parece válida")
    if host.lower() != "localhost" and "." not in host:
        raise ValueError("La URL no parece válida")
    return url

def url_recurso_usable(url: str | None) -> bool:

    if not url or not isinstance(url, str):
        return False
    try:
        return normalizar_url_recurso(url) is not None
    except ValueError:
        return False

def imagen_efectiva(imagen_url: str | None, categoria: str) -> str:

    if url_recurso_usable(imagen_url):
        return normalizar_url_recurso(imagen_url) or imagen_por_defecto(categoria)
    return imagen_por_defecto(categoria)

def logo_efectivo(logo_url: str | None) -> str | None:

    if not url_recurso_usable(logo_url):
        return None
    return normalizar_url_recurso(logo_url)
