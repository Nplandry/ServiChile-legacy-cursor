import uuid

from fastapi.testclient import TestClient

from app.infraestructura.persistencia.modelos import EntidadNegocio

def _negocio(session_factory) -> uuid.UUID:
    with session_factory() as s:
        negocio = EntidadNegocio(nombre="Proveedor TI Central", categoria="tecnologia")
        s.add(negocio)
        s.commit()
        return negocio.id

def _cuenta(client: TestClient, email: str, tipo: str = "persona") -> dict[str, str]:
    datos = {
        "email": email,
        "nombre": "Usuario Prueba",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": tipo},
    }
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    t = client.post(
        "/v1/auth/login", json={"email": email, "password": datos["password"]}
    ).json()
    return {"Authorization": f"Bearer {t['access_token']}"}

def _abrir(client: TestClient, headers, business_id) -> dict:
    r = client.post(
        "/v1/trabajos", json={"business_id": str(business_id)}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()

def _publicar(client: TestClient, headers, nombre: str = "Proveedor TI Central") -> str:
    r = client.post(
        "/v1/businesses",
        json={
            "nombre": nombre,
            "categoria": "tecnologia",
            "direccion": "Av. Siempre Viva 100",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]

def test_abrir_trabajo_devuelve_codigo_qr(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    h = {"Authorization": f"Bearer {token}"}
    trabajo = _abrir(client, h, bid)
    assert trabajo["estado"] == "abierto"
    assert len(trabajo["qr_token"]) >= 10

def test_abrir_negocio_inexistente_da_404(client: TestClient, token: str):
    h = {"Authorization": f"Bearer {token}"}
    r = client.post("/v1/trabajos", json={"business_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 404

def test_listar_mis_trabajos(client: TestClient, session_factory, token: str):
    bid = _negocio(session_factory)
    h = {"Authorization": f"Bearer {token}"}
    _abrir(client, h, bid)
    _abrir(client, h, bid)
    assert len(client.get("/v1/trabajos", headers=h).json()) == 2

def test_concretar_del_titular_da_score_100(client: TestClient, token_empresa: str):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid = _publicar(client, titular)
    cliente = _cuenta(client, "cliente@servichile.cl")
    trabajo = _abrir(client, cliente, bid)
    r = client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": trabajo["qr_token"]},
        headers=titular,
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "concretado"
    assert (
        client.get("/v1/perfil", headers=cliente).json()["score_confiabilidad"] == 100.0
    )
    ficha = next(x for x in client.get("/v1/businesses").json() if x["id"] == bid)
    assert ficha["trabajos_concretados"] == 1

    rep = client.get(f"/v1/businesses/{bid}/reputation", headers=titular)
    assert rep.status_code == 200, rep.text
    senal = next(
        o for o in rep.json()["observables"] if o["id"] == "trabajos_concretados"
    )
    assert senal["grupo"] == "plataforma"
    assert senal["etiqueta"] == "Trabajos Concretados en ServiChile"
    assert senal["score"] == 10
    assert client.get("/v1/businesses", params={"concretados": "1"}).json()
    assert (
        client.get("/v1/businesses", params={"concretados": "5"}).json() == []
    )

def test_no_concretado_baja_el_score(client: TestClient, token_empresa: str):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid = _publicar(client, titular)
    cliente = _cuenta(client, "cliente@servichile.cl")
    ok = _abrir(client, cliente, bid)
    fallo = _abrir(client, cliente, bid)
    client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": ok["qr_token"]},
        headers=titular,
    )
    r = client.post(
        f"/v1/businesses/{bid}/trabajos/{fallo['id']}/no-concretado", headers=titular
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "no_concretado"
    assert (
        client.get("/v1/perfil", headers=cliente).json()["score_confiabilidad"] == 50.0
    )

def test_concretar_de_otro_usuario_da_403(client: TestClient, token_empresa: str):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid = _publicar(client, titular)
    otro = _cuenta(client, "otro@servichile.cl")
    cliente = _cuenta(client, "cliente@servichile.cl")
    trabajo = _abrir(client, cliente, bid)
    r = client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": trabajo["qr_token"]},
        headers=otro,
    )
    assert r.status_code == 403

def test_concretar_en_negocio_no_reclamado_da_403(
    client: TestClient, session_factory, token: str
):
    bid = _negocio(session_factory)
    cliente = _cuenta(client, "cliente@servichile.cl")
    trabajo = _abrir(client, cliente, bid)
    r = client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": trabajo["qr_token"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403

def test_qr_de_otro_negocio_da_404(client: TestClient, token_empresa: str):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid_a = _publicar(client, titular, "Proveedor A")
    bid_b = _publicar(client, titular, "Proveedor B")
    cliente = _cuenta(client, "cliente@servichile.cl")
    trabajo_b = _abrir(client, cliente, bid_b)
    r = client.post(
        f"/v1/businesses/{bid_a}/trabajos/concretar",
        json={"qr_token": trabajo_b["qr_token"]},
        headers=titular,
    )
    assert r.status_code == 404

def test_trabajo_cerrado_no_se_puede_volver_a_cerrar(
    client: TestClient, token_empresa: str
):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid = _publicar(client, titular)
    cliente = _cuenta(client, "cliente@servichile.cl")
    trabajo = _abrir(client, cliente, bid)
    client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": trabajo["qr_token"]},
        headers=titular,
    )
    r = client.post(
        f"/v1/businesses/{bid}/trabajos/concretar",
        json={"qr_token": trabajo["qr_token"]},
        headers=titular,
    )
    assert r.status_code == 409

def test_trabajos_requieren_sesion(client: TestClient, session_factory):
    bid = _negocio(session_factory)
    assert (
        client.post("/v1/trabajos", json={"business_id": str(bid)}).status_code == 401
    )
    assert client.get("/v1/trabajos").status_code == 401
    assert (
        client.post(
            f"/v1/businesses/{bid}/trabajos/concretar", json={"qr_token": "x" * 12}
        ).status_code
        == 401
    )

def test_titular_lista_trabajos_del_negocio(client: TestClient, token_empresa: str):
    titular = {"Authorization": f"Bearer {token_empresa}"}
    bid = _publicar(client, titular)
    cliente = _cuenta(client, "lista-cliente@servichile.cl")
    _abrir(client, cliente, bid)
    r = client.get(f"/v1/businesses/{bid}/trabajos", headers=titular)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["estado"] == "abierto"
    ajeno = _cuenta(client, "ajeno-lista@servichile.cl")
    assert (
        client.get(f"/v1/businesses/{bid}/trabajos", headers=ajeno).status_code == 403
    )
