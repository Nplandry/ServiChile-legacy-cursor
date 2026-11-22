from fastapi.testclient import TestClient

def _registrar(
    client: TestClient, email="perfil@servichile.cl", perfil=None
) -> dict[str, str]:

    datos = {
        "email": email,
        "nombre": "Rosa",
        "password": "clave-perfil-123",
        "perfil": {"tipo_cuenta": "persona"},
    }

    if perfil is not None:

        datos["perfil"] = {"tipo_cuenta": "persona", **perfil}

    r = client.post("/v1/auth/registro", json=datos)

    assert r.status_code == 201, r.text

    t = client.post(
        "/v1/auth/login", json={"email": email, "password": datos["password"]}
    ).json()

    return {"Authorization": f"Bearer {t['access_token']}"}

def test_perfil_nuevo_es_reporte_nivel_1_basico(client: TestClient):

    h = _registrar(client, perfil={"edad": 68})

    cuerpo = client.get("/v1/perfil", headers=h).json()

    assert cuerpo["edad"] == 68

    assert cuerpo["rut_verificado"] is False

    assert cuerpo["telefono"] is None

    assert cuerpo["nivel_reporte"] == 1

    assert cuerpo["estado_reporte"] == "basico"

    assert cuerpo["score_confiabilidad"] is None

    assert "inmobiliaria_scoring" not in cuerpo

def test_campos_deprecados_preocupacion_proposito_rechazados(client: TestClient):

    h = _registrar(client, perfil={"edad": 70})

    r = client.patch(
        "/v1/perfil",
        json={"preocupacion": "seguros", "proposito": "asesorar"},
        headers=h,
    )
    assert r.status_code == 422

    cuerpo = client.get("/v1/perfil", headers=h).json()
    assert "preocupacion" not in cuerpo
    assert "proposito" not in cuerpo
    assert cuerpo["edad"] == 70

def test_patch_telefono_y_edad(client: TestClient):

    h = _registrar(client)

    r = client.patch(
        "/v1/perfil", json={"edad": 70, "telefono": "+56 9 1234 5678"}, headers=h
    )

    assert r.status_code == 200, r.text

    assert r.json()["edad"] == 70

    assert r.json()["telefono"] == "+56 9 1234 5678"

def test_patch_null_borra_el_telefono(client: TestClient):

    h = _registrar(client)

    client.patch("/v1/perfil", json={"telefono": "+56 9 1234 5678"}, headers=h)

    r = client.patch("/v1/perfil", json={"telefono": None}, headers=h)

    assert r.json()["telefono"] is None

def test_telefono_debe_empezar_con_mas_56(client: TestClient):

    h = _registrar(client)

    assert (
        client.patch("/v1/perfil", json={"telefono": "9 1234 5678"}, headers=h).status_code
        == 422
    )

    assert (
        client.patch(
            "/v1/perfil", json={"telefono": "56912345678"}, headers=h
        ).status_code
        == 422
    )

    r = client.patch(
        "/v1/perfil", json={"telefono": "+56912345678"}, headers=h
    )

    assert r.status_code == 200, r.text

    assert r.json()["telefono"] == "+56 9 1234 5678"

def test_rut_valido_queda_verificado(client: TestClient):

    h = _registrar(client)

    r = client.patch("/v1/perfil", json={"rut": "12.345.678-5"}, headers=h)

    assert r.status_code == 200, r.text

    assert r.json()["rut_verificado"] is True

def test_rut_con_dv_incorrecto_da_422(client: TestClient):

    h = _registrar(client)

    r = client.patch("/v1/perfil", json={"rut": "12345678-9"}, headers=h)

    assert r.status_code == 422

    assert "dígito verificador" in r.json()["detail"]

    assert client.get("/v1/perfil", headers=h).json()["rut_verificado"] is False

def test_rut_con_k_se_acepta_en_minuscula(client: TestClient):

    h = _registrar(client)

    assert (
        client.patch("/v1/perfil", json={"rut": "8765432-k"}, headers=h).status_code
        == 200
    )

def test_rut_ya_usado_por_otra_cuenta_da_409(client: TestClient):

    h1 = _registrar(client, "uno@servichile.cl")

    h2 = _registrar(client, "dos@servichile.cl")

    assert (
        client.patch("/v1/perfil", json={"rut": "12345678-5"}, headers=h1).status_code
        == 200
    )

    r = client.patch("/v1/perfil", json={"rut": "12345678-5"}, headers=h2)

    assert r.status_code == 409

def test_rut_verificado_no_se_puede_cambiar(client: TestClient):

    h = _registrar(client)

    client.patch("/v1/perfil", json={"rut": "12345678-5"}, headers=h)

    r = client.patch("/v1/perfil", json={"rut": "7654321-6"}, headers=h)

    assert r.status_code == 409

def test_rut_no_se_puede_borrar(client: TestClient):

    h = _registrar(client)

    assert client.patch("/v1/perfil", json={"rut": None}, headers=h).status_code == 422

def test_validaciones_del_perfil(client: TestClient):

    h = _registrar(client)

    assert client.patch("/v1/perfil", json={"edad": 13}, headers=h).status_code == 422

    assert client.patch("/v1/perfil", json={"edad": 121}, headers=h).status_code == 422

    assert (
        client.patch("/v1/perfil", json={"telefono": "abc"}, headers=h).status_code
        == 422
    )

    assert (
        client.patch("/v1/perfil", json={"campo_inventado": 1}, headers=h).status_code
        == 422
    )

def test_registro_con_perfil_invalido_no_crea_usuario(client: TestClient):

    datos = {
        "email": "x@servichile.cl",
        "nombre": "Ana",
        "password": "clave-segura-1",
        "perfil": {"tipo_cuenta": "persona", "edad": 5},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 422

    r = client.post(
        "/v1/auth/login",
        json={"email": "x@servichile.cl", "password": "clave-segura-1"},
    )

    assert r.status_code == 401

def test_registro_no_acepta_rut(client: TestClient):

    datos = {
        "email": "r@servichile.cl",
        "nombre": "Ana",
        "password": "clave-segura-1",
        "perfil": {"tipo_cuenta": "persona", "rut": "12345678-5"},
    }

    assert client.post("/v1/auth/registro", json=datos).status_code == 422

def test_perfil_requiere_sesion(client: TestClient):

    assert client.get("/v1/perfil").status_code == 401

    assert client.patch("/v1/perfil", json={"edad": 70}).status_code == 401

def test_perfil_es_privado(client: TestClient):

    h1 = _registrar(client, "uno@servichile.cl", {"edad": 70})

    h2 = _registrar(client, "dos@servichile.cl", {"edad": 40})

    client.patch("/v1/perfil", json={"edad": 99}, headers=h2)

    assert client.get("/v1/perfil", headers=h1).json()["edad"] == 70

def test_yo_incluye_el_reporte(client: TestClient):

    h = _registrar(client, perfil={"edad": 70})

    cuerpo = client.get("/v1/auth/yo", headers=h).json()

    assert cuerpo["perfil"]["nivel_reporte"] == 1

    assert cuerpo["perfil"]["estado_reporte"] == "basico"

    assert "password_hash" not in cuerpo

    assert "rut" not in cuerpo
