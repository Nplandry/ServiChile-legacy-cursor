

from __future__ import annotations

import logging

import httpx

from app.dominio.errores import PagoInformeError
from app.dominio.puertos import (
    TransaccionWebpayConfirmada,
    TransaccionWebpayCreada,
)

log = logging.getLogger(__name__)

COMMERCE_CODE_TEST = "597055555532"
API_KEY_TEST = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
HOST_TEST = "https://webpay3gint.transbank.cl"
PATH_TX = "/rswebpaytransaction/api/webpay/v1.2/transactions"

class PasarelaWebpayHttp:
    def __init__(
        self,
        *,
        commerce_code: str = COMMERCE_CODE_TEST,
        api_key: str = API_KEY_TEST,
        host: str = HOST_TEST,
        timeout: float = 25.0,
    ) -> None:
        self.commerce_code = commerce_code.strip() or COMMERCE_CODE_TEST
        self.api_key = api_key.strip() or API_KEY_TEST
        self.host = (host.strip() or HOST_TEST).rstrip("/")
        self.timeout = timeout

    def url_formulario(self, token: str = "") -> str:

        _ = token
        return f"{self.host}/webpayserver/initTransaction"

    def _headers(self) -> dict[str, str]:
        return {
            "Tbk-Api-Key-Id": self.commerce_code,
            "Tbk-Api-Key-Secret": self.api_key,
            "Content-Type": "application/json",
        }

    def crear(
        self, buy_order: str, session_id: str, amount: int, return_url: str
    ) -> TransaccionWebpayCreada:
        url = self.host + PATH_TX
        cuerpo = {
            "buy_order": buy_order,
            "session_id": session_id[:61],
            "amount": int(amount),
            "return_url": return_url,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, json=cuerpo, headers=self._headers())
        except httpx.HTTPError as e:
            log.exception("Transbank create falló")
            raise PagoInformeError(
                "No se pudo contactar a Transbank para iniciar el pago.",
                codigo="tbk_create_red",
                buy_order=buy_order,
            ) from e
        if r.status_code >= 400:
            raise PagoInformeError(
                f"Transbank rechazó la creación del pago (HTTP {r.status_code}).",
                codigo="tbk_create_http",
                buy_order=buy_order,
            )
        data = r.json() if r.content else {}
        token = str(data.get("token") or "").strip()
        destino = str(data.get("url") or "").strip()
        if not token or not destino:
            raise PagoInformeError(
                "Transbank no devolvió token/url de pago.",
                codigo="tbk_create_invalido",
                buy_order=buy_order,
            )
        return TransaccionWebpayCreada(token=token, url=destino)

    def confirmar(self, token: str) -> TransaccionWebpayConfirmada:
        url = f"{self.host}{PATH_TX}/{token}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.put(url, json={}, headers=self._headers())
        except httpx.HTTPError as e:
            log.exception("Transbank commit falló")
            raise PagoInformeError(
                "No se pudo confirmar el pago en Transbank.",
                codigo="tbk_commit_red",
            ) from e
        if r.status_code >= 400:
            raise PagoInformeError(
                f"Transbank rechazó la confirmación (HTTP {r.status_code}).",
                codigo="tbk_commit_http",
            )
        data = r.json() if r.content else {}
        card = data.get("card_detail") if isinstance(data.get("card_detail"), dict) else {}
        last4 = str(card.get("card_number") or "").strip()[-4:] or None
        try:
            response_code = int(data.get("response_code"))
        except (TypeError, ValueError):
            response_code = -1
        return TransaccionWebpayConfirmada(
            response_code=response_code,
            status=str(data.get("status") or ""),
            authorization_code=(
                str(data.get("authorization_code")).strip()
                if data.get("authorization_code") is not None
                else None
            ),
            payment_type_code=(
                str(data.get("payment_type_code")).strip()
                if data.get("payment_type_code") is not None
                else None
            ),
            card_last4=last4,
            buy_order=(
                str(data.get("buy_order")).strip()
                if data.get("buy_order") is not None
                else None
            ),
            detalle=str(data.get("status") or "") or None,
        )

class PasarelaWebpayMemoria:

    def __init__(self, *, autorizar: bool = True) -> None:
        self.autorizar = autorizar
        self._tokens: dict[str, str] = {}
        self._urls: dict[str, str] = {}

    def url_formulario(self, token: str = "") -> str:
        if token and token in self._urls:
            return self._urls[token]
        return "http://localhost/tbk-mock"

    def crear(
        self, buy_order: str, session_id: str, amount: int, return_url: str
    ) -> TransaccionWebpayCreada:
        token = "test-" + buy_order
        self._tokens[token] = buy_order
        destino = (
            return_url + ("&" if "?" in return_url else "?") + "token_ws=" + token
        )
        self._urls[token] = destino
        return TransaccionWebpayCreada(token=token, url=destino)

    def confirmar(self, token: str) -> TransaccionWebpayConfirmada:
        buy_order = self._tokens.get(token, token.replace("test-", "", 1))
        if self.autorizar:
            return TransaccionWebpayConfirmada(
                response_code=0,
                status="AUTHORIZED",
                authorization_code="123456",
                payment_type_code="VD",
                card_last4="6623",
                buy_order=buy_order,
            )
        return TransaccionWebpayConfirmada(
            response_code=-1,
            status="FAILED",
            buy_order=buy_order,
            detalle="Rechazado por pasarela de prueba",
        )
