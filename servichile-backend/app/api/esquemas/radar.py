from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

class InformeSalida(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enviado: bool
    destino: EmailStr
    qr_payload: str | None = None
    expires_at: datetime | None = None
