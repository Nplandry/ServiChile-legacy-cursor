

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization

EXTS = {".pem", ".crt", ".cer", ".cert", ".der"}

def _convert_p7b(path: Path, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / (path.stem.replace(" ", "_") + ".pem")
    for form in ("DER", "PEM"):
        r = subprocess.run(
            [
                "openssl",
                "pkcs7",
                "-inform",
                form,
                "-in",
                str(path),
                "-print_certs",
                "-out",
                str(tmp),
            ],
            capture_output=True,
        )
        if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            return tmp
    return None

def _load(data: bytes) -> list[x509.Certificate]:
    if b"BEGIN CERTIFICATE" in data:
        try:
            return list(x509.load_pem_x509_certificates(data))
        except Exception:
            try:
                return [x509.load_pem_x509_certificate(data)]
            except Exception:
                return []
    try:
        return [x509.load_der_x509_certificate(data)]
    except Exception:
        return []

def construir(fuentes: list[Path], destino: Path) -> int:
    seen: dict[str, x509.Certificate] = {}
    tmp_p7b = destino.parent / "_p7b_tmp"
    for raiz in fuentes:
        if not raiz.exists():
            continue
        paths = [raiz] if raiz.is_file() else list(raiz.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            suf = path.suffix.lower()
            if suf in {".p7b", ".p7c"}:
                conv = _convert_p7b(path, tmp_p7b)
                if not conv:
                    continue
                path = conv
                suf = ".pem"
            if suf not in EXTS:
                head = path.read_bytes()[:80]
                if b"BEGIN CERTIFICATE" not in head and not (
                    head and head[0] == 0x30
                ):
                    continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            for cert in _load(data):
                fp = cert.fingerprint(hashes.SHA256()).hex()
                seen[fp] = cert

    parts = [
        "# Bóveda de confianza Chile — CA acreditadas FEA (raíces e intermedios).\n",
        "# Público: no contiene llaves privadas.\n\n",
    ]
    for _fp, cert in sorted(seen.items(), key=lambda kv: kv[0]):
        try:
            subj = cert.subject.rfc4514_string()
        except Exception:
            subj = str(cert.subject)
        parts.append(f"# {subj}\n")
        pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        parts.append(pem if pem.endswith("\n") else pem + "\n")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("".join(parts), encoding="utf-8")
    return len(seen)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fuentes",
        nargs="+",
        type=Path,
        help="Carpetas/archivos con .pem/.crt/.cer/.p7b",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("app/infraestructura/certs/ca_chile.pem"),
    )
    args = parser.parse_args()
    n = construir(args.fuentes, args.out)
    print(f"unique={n} -> {args.out}")
    return 0 if n else 1

if __name__ == "__main__":
    sys.exit(main())
