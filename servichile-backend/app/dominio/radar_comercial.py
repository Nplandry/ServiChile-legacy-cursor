

from __future__ import annotations

import re
from dataclasses import dataclass

_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PROPOSITOS = {
    "cotizar": "Cotizar un proyecto o servicio",
    "proveedor": "Evaluarla como proveedor fijo",
    "licitacion": "Licitación formal",
}
MONTOS = {
    "bajo": "Menos de $1.000.000",
    "medio": "Entre $1.000.000 y $5.000.000",
    "alto": "Más de $5.000.000",
}
PLAZOS = {
    "semana": "Esta semana (presupuesto aprobado)",
    "mes": "Este mes (en evaluación)",
    "cotizando": "Solo cotizando",
}

@dataclass(frozen=True)
class AlertaRadar:
    tipo: str
    titulo: str
    detalle: str

@dataclass(frozen=True)
class RadarSimulado:
    ciberseguridad: float
    legal: float
    contratos: float
    alertas: tuple[AlertaRadar, ...]

def semilla(texto: str) -> int:
    h = 2166136261
    for ch in texto or "x":
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h

def _nota(seed: int, base: int, desplazamiento: int, modulo: int) -> float:
    valor = (base + ((seed >> desplazamiento) % modulo)) / 10
    return min(5.0, round(valor, 1))

def _slug(nombre: str) -> str:
    limpio = "".join(ch for ch in (nombre or "").lower() if ch.isalnum())
    return limpio[:10] or "pyme"

def construir_radar(clave: str, nombre: str) -> RadarSimulado:
    seed = semilla(clave or nombre or "x")
    dominio = _slug(nombre)
    return RadarSimulado(
        ciberseguridad=_nota(seed, 38, 0, 12),
        legal=_nota(seed, 22, 3, 18),
        contratos=_nota(seed, 32, 5, 16),
        alertas=(
            AlertaRadar(
                "Legal",
                "Se detectó 1 demanda laboral y 1 deuda previsional en los últimos 12 meses.",
                "Deuda previsional estimada $2.480.000 · Tribunal Laboral de Santiago · "
                f"Causa T-2025-{1000 + (seed % 800)} · Dato simulado, no es un certificado.",
            ),
            AlertaRadar(
                "Técnica",
                "Dominio con 14 credenciales filtradas y sin protección DMARC.",
                "14 correos @dominio en breach 2025 · DMARC ausente · SPF parcial · "
                f"Ejemplo filtrado: operaciones@{dominio}.cl · Dato simulado.",
            ),
            AlertaRadar(
                "Contractual",
                "Se identificó 1 multa administrativa vigente sin plan de remediación.",
                "Multa SII/DT simulada $890.000 · "
                f"Folio ADM-{4000 + (seed % 500)} · Dato simulado.",
            ),
        ),
    )

def correo_opcional(valor: str | None) -> str | None:
    from app.dominio.errores import RadarInvalido

    if valor is None or not str(valor).strip():
        return None
    correo = str(valor).strip().lower()
    if len(correo) > 254 or not _CORREO.match(correo):
        raise RadarInvalido("Ingrese un correo válido.")
    return correo

def mensaje_contacto(
    *,
    comprador: str,
    correo: str,
    empresa: str,
    proposito: str,
    monto: str,
    plazo: str,
    nota: float | None,
    extra: str,
) -> tuple[str, str]:
    from app.dominio.errores import RadarInvalido

    if proposito not in PROPOSITOS or monto not in MONTOS or plazo not in PLAZOS:
        raise RadarInvalido("Revise el motivo, el monto y el plazo.")
    nota_txt = (
        "La ficha todavía no tiene índice de transparencia."
        if nota is None
        else (
            f"La ficha muestra ★ {nota:.1f}. Ese índice sale del rater y de los documentos. "
            "No es este radar de riesgo."
        )
    )
    extra_limpio = " ".join((extra or "").split())[:500]
    lineas = [
        f"Hola {empresa},",
        "",
        f"Soy {comprador} ({correo}). Les escribo desde ServiChile.",
        "",
        f"Para qué: {PROPOSITOS[proposito]}",
        f"Monto aproximado: {MONTOS[monto]}",
        f"Cuándo: {PLAZOS[plazo]}",
    ]
    if extra_limpio:
        lineas.extend(["", extra_limpio])
    lineas.extend(["", nota_txt, "", "Quedo atento.", comprador])
    asunto = f"Consulta desde ServiChile: {comprador} escribe a {empresa}"
    return asunto[:200], "\n".join(lineas)

_CATEGORIAS = {
    "tecnologia": "Tecnología",
    "industria": "Minería e industria",
    "construccion": "Construcción",
    "servicios-profesionales": "Profesionales",
    "logistica": "Logística",
}
_OFERTA = {
    "mineria": "Minería",
    "retail": "Retail",
    "salud": "Salud",
    "construccion": "Construcción",
    "tecnologia": "Tecnología",
    "sector-publico": "Sector público",
    "cotizacion-directa": "Cotización directa",
    "contrato-recurrente": "Contrato recurrente",
    "licitacion-oc": "Licitación u orden de compra",
    "factura-electronica": "Factura electrónica",
    "bajo": "Menos de $1.000.000",
    "medio": "Entre $1.000.000 y $5.000.000",
    "alto": "Más de $5.000.000",
    "menos-2h": "Menos de 2 horas",
    "en-el-dia": "En el día",
    "24-48h": "24 a 48 horas",
}

def _etiqueta(valor: str | None) -> str:
    if not valor:
        return "—"
    return _OFERTA.get(valor, valor)

def _lista(valores: tuple[str, ...] | list[str]) -> str:
    textos = [_etiqueta(v) for v in valores if v]
    return ", ".join(textos) if textos else "—"

@dataclass(frozen=True)
class ObservableReporte:
    id: str
    etiqueta: str
    detalle: str
    score: int
    grupo: str

@dataclass(frozen=True)
class DatosReporte:

    nombre: str
    categoria: str
    rut: str | None
    direccion: str | None
    telefono: str | None
    sitio_web: str | None
    descripcion: str | None
    indice: float
    indice_pct: int
    docs_verificados: int
    docs_total: int
    servicios: tuple[str, ...]
    industrias: tuple[str, ...]
    contrataciones: tuple[str, ...]
    monto: str | None
    plazo: str | None
    referencias: tuple[str, ...]
    observables: tuple[ObservableReporte, ...] = ()
    referencia: str = "SC-E-00000000"
    emitido: object | None = None
    qr_payload: str | None = None
    qr_expira: object | None = None

def lineas_reporte(datos: DatosReporte) -> list[str]:

    descripcion = " ".join((datos.descripcion or "").split()) or "Sin descripción"
    return [
        "ServiChile",
        "Reporte de transparencia empresarial",
        "",
        f"Empresa: {datos.nombre}",
        f"Categoría: {_CATEGORIAS.get(datos.categoria, datos.categoria or '—')}",
        f"RUT: {datos.rut or '—'}",
        f"Dirección: {datos.direccion or '—'}",
        f"Teléfono: {datos.telefono or '—'}",
        f"Sitio web: {datos.sitio_web or '—'}",
        f"Descripción: {descripcion}",
        "",
        "Resumen de transparencia",
        f"Índice global: {datos.indice:.1f} / 10",
        f"Señales: {datos.indice_pct}%",
        f"Documentos legales: {datos.docs_verificados} de {datos.docs_total}",
        "",
        "Oferta declarada por la empresa. No forma parte del índice.",
        f"Servicios: {_lista(datos.servicios)}",
        f"Le vende a: {_lista(datos.industrias)}",
        f"Cómo se contrata: {_lista(datos.contrataciones)}",
        f"Monto que acepta: {_etiqueta(datos.monto)}",
        f"Plazo de cotización: {_etiqueta(datos.plazo)}",
        f"Referencias: {_lista(datos.referencias)}",
        "",
        "Documento informativo generado por ServiChile.",
        "El índice refleja señales públicas y documentos del perfil.",
        "No sustituye auditorías oficiales.",
    ]

