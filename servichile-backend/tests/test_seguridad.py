import statistics

import time

from fastapi.testclient import TestClient

from sqlalchemy import select

from app.api import dependencias

from app.infraestructura.persistencia.modelos import Usuario

from app.principal import app

class SinLimite:

    def permitir(self, clave, limite, ventana_s=60):

        return True

def _hash_de(session_factory, email: str) -> str:

    with session_factory() as s:

        return s.scalar(select(Usuario.password_hash).where(Usuario.email == email))

def test_sal_distinto_para_la_misma_contrasena(client: TestClient, session_factory):

    for email in ("uno@servichile.cl", "dos@servichile.cl"):

        client.post(
            "/v1/auth/registro",
            json={
                "email": email,
                "nombre": "Ana",
                "password": "misma-clave-123",
                "perfil": {"tipo_cuenta": "persona"},
            },
        )

    h1 = _hash_de(session_factory, "uno@servichile.cl")

    h2 = _hash_de(session_factory, "dos@servichile.cl")

    assert h1 != h2

    sal1, sal2 = (h1.split("$")[4], h2.split("$")[4])

    assert sal1 != sal2

    assert len(sal1) >= 22

def test_no_hay_sal_fijo_en_el_codigo():

    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1] / "app"

    for archivo in raiz.rglob("*.py"):

        texto = archivo.read_text(encoding="utf-8").lower()

        assert (
            "salt=" not in texto and "salt =" not in texto
        ), f"posible sal fija en {archivo}"

def test_hash_no_contiene_la_contrasena(client: TestClient, session_factory):

    client.post(
        "/v1/auth/registro",
        json={
            "email": "h@servichile.cl",
            "nombre": "Ana",
            "password": "clave-visible-99",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    assert "clave-visible-99" not in _hash_de(session_factory, "h@servichile.cl")

def test_mismo_mensaje_correo_inexistente_y_clave_incorrecta(client: TestClient):

    client.post(
        "/v1/auth/registro",
        json={
            "email": "real@servichile.cl",
            "nombre": "Ana",
            "password": "clave-real-123",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    a = client.post(
        "/v1/auth/login",
        json={"email": "real@servichile.cl", "password": "otra-clave-999"},
    )

    b = client.post(
        "/v1/auth/login",
        json={"email": "fantasma@servichile.cl", "password": "otra-clave-999"},
    )

    assert a.status_code == b.status_code == 401

    assert a.json() == b.json() == {"detail": "Correo o contraseña incorrectos."}

def test_usuario_inactivo_recibe_el_mismo_error(client: TestClient, session_factory):

    client.post(
        "/v1/auth/registro",
        json={
            "email": "baja@servichile.cl",
            "nombre": "Ana",
            "password": "clave-baja-123",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    with session_factory() as s:

        s.query(Usuario).filter(Usuario.email == "baja@servichile.cl").update(
            {"activo": False}
        )

        s.commit()

    r = client.post(
        "/v1/auth/login",
        json={"email": "baja@servichile.cl", "password": "clave-baja-123"},
    )

    assert r.status_code == 401

    assert r.json() == {"detail": "Correo o contraseña incorrectos."}

def _mediana_login(client: TestClient, email: str, repeticiones: int) -> float:

    tiempos = []

    for _ in range(repeticiones):

        inicio = time.perf_counter()

        client.post(
            "/v1/auth/login", json={"email": email, "password": "clave-equivocada"}
        )

        tiempos.append(time.perf_counter() - inicio)

    return statistics.median(tiempos)

def test_tiempo_similar_con_y_sin_cuenta(client: TestClient):

    datos = {
        "email": "tiempo@servichile.cl",
        "nombre": "Ana",
        "password": "clave-tiempo-1",
        "perfil": {"tipo_cuenta": "persona"},
    }

    client.post("/v1/auth/registro", json=datos)

    app.dependency_overrides[dependencias.obtener_limite_solicitudes] = lambda: SinLimite()

    try:

        _mediana_login(client, "tiempo@servichile.cl", 2)

        con_cuenta = _mediana_login(client, "tiempo@servichile.cl", 7)

        sin_cuenta = _mediana_login(client, "nadie@servichile.cl", 7)

    finally:

        app.dependency_overrides.pop(dependencias.obtener_limite_solicitudes, None)

    cociente = max(con_cuenta, sin_cuenta) / min(con_cuenta, sin_cuenta)

    assert (
        cociente < 1.5
    ), f"con cuenta {con_cuenta:.3f}s vs sin cuenta {sin_cuenta:.3f}s"

def test_limite_por_correo(client: TestClient):

    codigos = [
        client.post(
            "/v1/auth/login", json={"email": "x@servichile.cl", "password": "x"}
        ).status_code
        for _ in range(6)
    ]

    assert codigos[:5] == [401] * 5

    assert codigos[5] == 429

def test_limite_por_ip_aunque_cambie_el_correo(client: TestClient):

    codigos = [
        client.post(
            "/v1/auth/login", json={"email": f"n{i}@servichile.cl", "password": "x"}
        ).status_code
        for i in range(21)
    ]

    assert codigos[:20] == [401] * 20

    assert codigos[20] == 429

def test_limite_registro_por_ip(client: TestClient, monkeypatch):

    from app.infraestructura import limite_solicitudes

    class RelojFijo:

        @staticmethod
        def time() -> float:

            return 1000000.0

    monkeypatch.setattr(limite_solicitudes, "time", RelojFijo)

    codigos = [
        client.post(
            "/v1/auth/registro",
            json={
                "email": f"r{i}@servichile.cl",
                "nombre": "Ana",
                "password": "clave-registro-1",
                "perfil": {"tipo_cuenta": "persona"},
            },
        ).status_code
        for i in range(21)
    ]

    assert codigos[20] == 429

    assert codigos[0] == 201

def test_respuesta_429_incluye_retry_after(client: TestClient):

    for _ in range(5):

        client.post(
            "/v1/auth/login", json={"email": "rl@servichile.cl", "password": "x"}
        )

    r = client.post(
        "/v1/auth/login", json={"email": "rl@servichile.cl", "password": "x"}
    )

    assert r.status_code == 429

    assert r.headers["retry-after"] == "60"

def _settings_con_proxy(valor: bool):

    from app.configuracion import obtener_configuracion

    return obtener_configuracion().model_copy(update={"trust_proxy": valor})

def test_sin_proxy_de_confianza_se_ignora_x_forwarded_for(client: TestClient):

    from app.configuracion import obtener_configuracion

    app.dependency_overrides[obtener_configuracion] = lambda: _settings_con_proxy(False)

    try:

        codigos = [
            client.post(
                "/v1/auth/login",
                json={"email": f"s{i}@servichile.cl", "password": "x"},
                headers={"X-Forwarded-For": f"10.0.0.{i}"},
            ).status_code
            for i in range(21)
        ]

    finally:

        app.dependency_overrides.pop(obtener_configuracion, None)

    assert codigos[20] == 429

def test_con_proxy_usa_la_ip_agregada_por_el_proxy_no_la_falsificada(
    client: TestClient,
):

    from app.configuracion import obtener_configuracion

    app.dependency_overrides[obtener_configuracion] = lambda: _settings_con_proxy(True)

    try:

        codigos = [
            client.post(
                "/v1/auth/login",
                json={"email": f"p{i}@servichile.cl", "password": "x"},
                headers={"X-Forwarded-For": f"10.9.9.{i}, 203.0.113.7"},
            ).status_code
            for i in range(21)
        ]

        otros = [
            client.post(
                "/v1/auth/login",
                json={"email": f"q{i}@servichile.cl", "password": "x"},
                headers={"X-Forwarded-For": f"203.0.113.{i + 50}"},
            ).status_code
            for i in range(3)
        ]

    finally:

        app.dependency_overrides.pop(obtener_configuracion, None)

    assert codigos[20] == 429

    assert otros == [401, 401, 401]
