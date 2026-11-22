from fastapi.testclient import TestClient

def test_registro_normaliza_email_y_no_expone_hash(client: TestClient):

    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "Ana@Mail.CL",
            "nombre": " Ana ",
            "password": "12345678",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    assert r.status_code == 201

    body = r.json()

    assert body["email"] == "ana@mail.cl"

    assert body["nombre"] == "Ana"

    assert "password_hash" not in body

def test_registro_duplicado(client: TestClient):

    datos = {
        "email": "a@b.cl",
        "nombre": "Ana",
        "password": "12345678",
        "perfil": {"tipo_cuenta": "persona"},
    }

    client.post("/v1/auth/registro", json=datos)

    assert client.post("/v1/auth/registro", json=datos).status_code == 409

def test_registro_password_corta(client: TestClient):

    r = client.post(
        "/v1/auth/registro",
        json={
            "email": "a@b.cl",
            "nombre": "Ana",
            "password": "corta",
            "perfil": {"tipo_cuenta": "persona"},
        },
    )

    assert r.status_code == 422

def test_login_y_yo(client: TestClient, token: str):

    r = client.get("/v1/auth/yo", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200

    assert r.json()["email"] == "maria@servichile.cl"

def test_login_password_incorrecta(client: TestClient, token: str):

    r = client.post(
        "/v1/auth/login",
        json={"email": "maria@servichile.cl", "password": "otra-clave"},
    )

    assert r.status_code == 401

def test_login_email_inexistente_mismo_error(client: TestClient):

    r = client.post(
        "/v1/auth/login", json={"email": "nadie@servichile.cl", "password": "x"}
    )

    assert r.status_code == 401

    assert r.json()["detail"] == "Correo o contraseña incorrectos."

def test_token_invalido(client: TestClient):

    assert (
        client.get(
            "/v1/auth/yo", headers={"Authorization": "Bearer basura"}
        ).status_code
        == 401
    )

    assert client.get("/v1/auth/yo").status_code == 401

def test_rate_limit_login(client: TestClient):

    codigos = [
        client.post(
            "/v1/auth/login", json={"email": "x@servichile.cl", "password": "x"}
        ).status_code
        for _ in range(6)
    ]

    assert codigos[:5] == [401] * 5

    assert codigos[5] == 429
