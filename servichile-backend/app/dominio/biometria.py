

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

BIOMETRIA_MAX_BYTES = 5 * 1024 * 1024
BIOMETRIA_MAX_LADO_DEFAULT = 640
BIOMETRIA_JPEG_QUALITY_DEFAULT = 75
BIOMETRIA_RETENCION_DIAS_DEFAULT = 180
BIOMETRIA_CONTENT_TYPE = "image/jpeg"

@dataclass(frozen=True)
class MetaBiometria:
    ruta_relativa: str
    sha256: str
    bytes_: int
    ancho: int
    alto: int
    content_type: str = BIOMETRIA_CONTENT_TYPE

def retener_hasta(
    desde: datetime | None = None, *, dias: int = BIOMETRIA_RETENCION_DIAS_DEFAULT
) -> datetime:
    base = desde or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(days=max(1, int(dias)))
