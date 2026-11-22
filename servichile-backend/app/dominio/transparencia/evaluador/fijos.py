

from __future__ import annotations

HINTS_FIJOS: dict[str, float] = {
    "cyb_https": 100.0,
    "cyb_hsts": 70.0,
    "cyb_csp": 55.0,
    "cyb_xfo": 60.0,
    "cyb_xcto": 65.0,
    "cyb_referrer": 50.0,
    "cyb_cookies": 55.0,
    "cyb_mixed": 70.0,
    "con_privacy": 75.0,
    "con_ley_21719": 45.0,
    "con_tyc": 70.0,
    "con_sla": 40.0,
    "con_dpa": 35.0,
    "con_clausulas": 55.0,
    "con_contacto_datos": 50.0,
    "con_cookies_notice": 60.0,
    "fis_places_exists": 80.0,
    "fis_rating": 72.0,
    "fis_reviews": 55.0,
    "fis_address": 90.0,
    "fis_phone": 85.0,
    "fis_hours": 60.0,
    "dig_website": 100.0,
    "est_proveedor": 100.0,
}

def hints_fijos() -> dict[str, float]:
    return dict(HINTS_FIJOS)
