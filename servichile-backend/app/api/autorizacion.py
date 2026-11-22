

from fastapi import HTTPException, status

from app.dominio.entidades import Usuario

from app.dominio.tipo_cuenta import es_proveedor, tipo_de_usuario

SOLO_PROVEEDOR = (
    "Solo una cuenta proveedor puede crear fichas en el marketplace."
)

def exige_cuenta_proveedor(usuario: Usuario) -> None:

    if not es_proveedor(tipo_de_usuario(usuario)):

        raise HTTPException(status.HTTP_403_FORBIDDEN, SOLO_PROVEEDOR)
