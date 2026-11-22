

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.dominio.puertos import RegistroHashPades

def registrar_hash_unico(
    puerto: RegistroHashPades,
    sha256: str | None,
    *,
    scope: str,
    tipo: str,
    usuario_id: uuid.UUID | None = None,
    business_id: uuid.UUID | None = None,
    al_rechazar: Callable[[], Exception],
) -> None:
    if not sha256:
        return
    if not puerto.registrar_hash_pades(
        sha256,
        scope=scope,
        tipo=tipo,
        usuario_id=usuario_id,
        business_id=business_id,
    ):
        raise al_rechazar()
