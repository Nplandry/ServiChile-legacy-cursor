

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata

from app.infraestructura.trust_vault import ruta_ca_default

def pdf_con_texto(texto: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    page = writer.pages[0]
    safe = (
        texto.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\n", ") Tj T* (")
    )
    content = f"BT /F1 10 Tf 50 750 Td 14 TL ({safe}) Tj ET"
    stream = DecodedStreamObject()
    stream.set_data(content.encode("latin-1", errors="replace"))
    page[NameObject("/Contents")] = stream
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()

def crear_ca_y_hoja(
    *,
    leaf_cn: str,
    leaf_org: str | None = None,
) -> tuple[bytes, bytes, bytes]:

    now = datetime.now(timezone.utc)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CL"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ServiChile Test CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, "ServiChile Test Root CA"),
        ]
    )
    root_cert = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .sign(root_key, hashes.SHA256())
    )

    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_attrs = [
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CL"),
        x509.NameAttribute(NameOID.COMMON_NAME, leaf_cn),
    ]
    if leaf_org:
        leaf_attrs.insert(
            1, x509.NameAttribute(NameOID.ORGANIZATION_NAME, leaf_org)
        )
    leaf_name = x509.Name(leaf_attrs)
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )

    root_pem = root_cert.public_bytes(serialization.Encoding.PEM)
    leaf_pem = leaf_cert.public_bytes(serialization.Encoding.PEM)
    key_pem = leaf_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return root_pem, leaf_pem, key_pem

def vault_con_raiz_prueba(destino: Path, root_pem: bytes) -> Path:
    base = ruta_ca_default()
    contenido = base.read_bytes() if base.is_file() else b""
    destino.write_bytes(contenido + b"\n" + root_pem)
    return destino

def firmar_pdf_pades(
    pdf_bytes: bytes,
    *,
    common_name: str,
    organization: str | None = None,
    leaf_cert_pem: bytes | None = None,
    leaf_key_pem: bytes | None = None,
) -> bytes:
    if leaf_cert_pem is None or leaf_key_pem is None:
        _root, leaf_cert_pem, leaf_key_pem = crear_ca_y_hoja(
            leaf_cn=common_name, leaf_org=organization
        )
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        key_path = base / "key.pem"
        cert_path = base / "cert.pem"
        key_path.write_bytes(leaf_key_pem)
        cert_path.write_bytes(leaf_cert_pem)
        signer = signers.SimpleSigner.load(str(key_path), str(cert_path))
        out = BytesIO()
        writer = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
        pdf_signer = signers.PdfSigner(
            PdfSignatureMetadata(field_name="SigTest"), signer=signer
        )
        pdf_signer.sign_pdf(writer, output=out)
        return out.getvalue()
