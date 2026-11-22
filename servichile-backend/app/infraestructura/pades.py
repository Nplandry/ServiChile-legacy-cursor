

from __future__ import annotations

import logging
from io import BytesIO

from app.dominio.pades import (
    ResultadoPades,
    emisor_coincide,
    entidad_de,
    sha256_hex,
)
from app.infraestructura.trust_vault import (
    obtener_contexto_validacion,
    ruta_ca_default,
)

logger = logging.getLogger(__name__)

def _nombre_cert(cert) -> str:
    try:
        return str(cert.subject.human_friendly)
    except Exception:
        return str(getattr(cert, "subject", "") or "")

def _issuer_cert(cert) -> str:
    try:
        return str(cert.issuer.human_friendly)
    except Exception:
        return str(getattr(cert, "issuer", "") or "")

def _bytes_cubiertos_por_firma(pdf_bytes: bytes, sig) -> bytes:

    br = list(getattr(sig, "byte_range", []) or [])
    if len(br) != 4:
        return pdf_bytes
    start1, len1, start2, len2 = (int(x) for x in br)
    buf = BytesIO(pdf_bytes)
    buf.seek(start1)
    parte1 = buf.read(len1)
    buf.seek(start2)
    parte2 = buf.read(len2)

    hueco = max(0, start2 - (start1 + len1))
    return parte1 + (b" " * hueco) + parte2

def verificar_firma_pades(
    pdf_bytes: bytes,
    *,
    perfil: str,
    ca_pem_path: str | None = None,
) -> ResultadoPades:

    digest = sha256_hex(pdf_bytes)
    vacio = ResultadoPades(
        ok=False,
        intact=False,
        trusted=False,
        coverage_ok=False,
        entidad_emisora=None,
        subject=None,
        issuer=None,
        sha256_hash=digest,
        motivo="",
        senales=(),
        pdf_firmado_bytes=None,
    )

    if not pdf_bytes.startswith(b"%PDF"):
        return ResultadoPades(
            **{**vacio.__dict__, "motivo": "El archivo no es un PDF válido.", "senales": ("no-pdf",)}
        )

    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
        from pyhanko.sign.validation.status import SignatureCoverageLevel
    except ImportError:
        logger.exception("pyhanko no instalado")
        return ResultadoPades(
            **{
                **vacio.__dict__,
                "motivo": "Verificación de firma electrónica no disponible.",
                "senales": ("pades-no-disponible",),
            }
        )

    pem = ca_pem_path or str(ruta_ca_default())
    try:
        vc = obtener_contexto_validacion(pem)
    except Exception as error:
        logger.exception("No se pudo cargar bóveda CA: %s", error)
        return ResultadoPades(
            **{
                **vacio.__dict__,
                "motivo": "Bóveda de certificados CA de Chile no disponible.",
                "senales": ("ca-no-disponible",),
            }
        )

    buffer = BytesIO(pdf_bytes)
    try:
        reader = PdfFileReader(buffer)
        firmas = list(reader.embedded_signatures)
    except Exception as error:
        logger.info("PDF PAdES ilegible: %s", error)
        return ResultadoPades(
            **{
                **vacio.__dict__,
                "motivo": "No se pudo leer el PDF para validar la firma electrónica.",
                "senales": ("pades-ilegible",),
            }
        )

    if not firmas:
        return ResultadoPades(
            **{
                **vacio.__dict__,
                "motivo": (
                    "El PDF no trae firma electrónica avanzada (PAdES). "
                    "Suba el PDF oficial sin editar."
                ),
                "senales": ("sin-firma-pades",),
            }
        )

    sig = firmas[-1]
    subject = None
    issuer = None

    try:
        status = validate_pdf_signature(sig, signer_validation_context=vc)
    except Exception as error:
        logger.info("Firma PAdES no validable: %s", error)
        return ResultadoPades(
            **{
                **vacio.__dict__,
                "motivo": (
                    "No se pudo validar la firma electrónica del PDF "
                    "(cadena o integridad)."
                ),
                "senales": ("pades-error-validacion",),
            }
        )

    cert = getattr(status, "signing_cert", None)
    subject = _nombre_cert(cert) if cert else None
    issuer = _issuer_cert(cert) if cert else None
    coverage = getattr(status, "coverage", None) or sig.evaluate_signature_coverage()

    if not status.intact:
        return ResultadoPades(
            ok=False,
            intact=False,
            trusted=bool(getattr(status, "trusted", False)),
            coverage_ok=False,
            entidad_emisora=None,
            subject=subject,
            issuer=issuer,
            sha256_hash=digest,
            motivo=(
                "La firma electrónica no es íntegra: el PDF fue alterado "
                "después de firmarse."
            ),
            senales=("pades-alterada",),
        )

    if coverage != SignatureCoverageLevel.ENTIRE_FILE:
        return ResultadoPades(
            ok=False,
            intact=True,
            trusted=bool(getattr(status, "trusted", False)),
            coverage_ok=False,
            entidad_emisora=None,
            subject=subject,
            issuer=issuer,
            sha256_hash=digest,
            motivo=(
                "La firma no cubre el 100% del archivo (posible modificación "
                "incremental / PDF shadow). Suba el PDF oficial sin anexos."
            ),
            senales=("pades-coverage-parcial", str(coverage)),
        )

    if not bool(getattr(status, "trusted", False)):
        return ResultadoPades(
            ok=False,
            intact=True,
            trusted=False,
            coverage_ok=True,
            entidad_emisora=None,
            subject=subject,
            issuer=issuer,
            sha256_hash=digest,
            motivo=(
                "El certificado firmante no encadena a una Autoridad "
                "Certificadora acreditada de Chile (posible autofirma)."
            ),
            senales=("pades-no-confiable",),
        )

    if not emisor_coincide(subject or "", issuer or "", perfil):
        return ResultadoPades(
            ok=False,
            intact=True,
            trusted=True,
            coverage_ok=True,
            entidad_emisora=None,
            subject=subject,
            issuer=issuer,
            sha256_hash=digest,
            motivo=(
                "La firma es confiable, pero el titular del certificado no "
                "corresponde al organismo esperado para este documento."
            ),
            senales=("pades-intacta", "pades-trusted", "emisor-no-reconocido"),
        )

    entidad = entidad_de(perfil)
    firmado = _bytes_cubiertos_por_firma(pdf_bytes, sig)
    return ResultadoPades(
        ok=True,
        intact=True,
        trusted=True,
        coverage_ok=True,
        entidad_emisora=entidad,
        subject=subject,
        issuer=issuer,
        sha256_hash=digest,
        motivo=f"Firma PAdES íntegra, cobertura total y confiable. Emisor: {entidad}.",
        senales=(
            "pades-intacta",
            "pades-entire-file",
            "pades-trusted",
            "emisor-oficial",
            "sha256",
        ),
        pdf_firmado_bytes=firmado,
    )
