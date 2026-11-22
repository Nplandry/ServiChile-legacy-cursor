from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.dominio.docs_empresa import validar_doc_empresa

_TEXTO_CONSTITUCION = """
ESCRITURA PUBLICA DE CONSTITUCION DE SOCIEDAD
Notaria de Santiago
Razon social: Demo SpA
RUT 76.123.456-0
Estatutos de la sociedad por acciones.
Registro de Comercio y Diario Oficial.
Fecha 15/01/2025.
"""

_TEXTO_PATENTE = """
ILUSTRE MUNICIPALIDAD DE SANTIAGO
Patente municipal comercial
Permiso de funcionamiento y giro comercial.
RUT 76.123.456-0
Fecha 01/03/2026
Direccion de rentas municipales.
"""

_TEXTO_SII = """
SERVICIO DE IMPUESTOS INTERNOS
Certificado de inicio de actividades del contribuyente ante el SII.
Formulario oficial de impuestos internos para inicio de actividades comerciales.
RUT 76.123.456-0
Giro: servicios profesionales y consultoria
Fecha 10/11/2026
El contribuyente declara el comienzo de sus operaciones ante el Servicio de Impuestos Internos.
Empresa vigente.
"""

def _pdf_texto(texto: str) -> bytes:
    from tests.helpers_pades import pdf_con_texto

    return pdf_con_texto(texto)

def test_validar_constitucion_reglas_ok():
    r = validar_doc_empresa(
        tipo="constitucion",
        texto=_TEXTO_CONSTITUCION,
        nombre_empresa="Demo SpA",
        rut_empresa="76123456-0",
        pades_ok=True,
        entidad_emisora="NOTARIA_RES",
        sha256_hash="abc",
    )
    assert r.aceptado is True

def test_validar_patente_ok():
    r = validar_doc_empresa(
        tipo="patente", texto=_TEXTO_PATENTE, rut_empresa="76123456-0"
    )
    assert r.aceptado is True

def test_validar_sii_ok():
    r = validar_doc_empresa(
        tipo="inicio_actividades",
        texto=_TEXTO_SII,
        rut_empresa="76123456-0",
        pades_ok=True,
        entidad_emisora="SII",
        sha256_hash="abc",
    )
    assert r.aceptado is True
    assert r.verificado_criptograficamente is True
    assert "pades-intacta" in r.senales

def test_validar_sii_sin_pades_falla():
    r = validar_doc_empresa(tipo="inicio_actividades", texto=_TEXTO_SII)
    assert r.aceptado is False

def test_validar_tipo_cruzado_falla():
    r = validar_doc_empresa(tipo="patente", texto=_TEXTO_CONSTITUCION)
    assert r.aceptado is False

def _crear_proveedor(client: TestClient) -> tuple[str, str]:
    import uuid

    email = f"prov-{uuid.uuid4().hex[:10]}@servichile.cl"
    datos = {
        "email": email,
        "nombre": "Proveedor Docs SpA",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "proveedor"},
    }
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    r = client.post(
        "/v1/auth/login",
        json={"email": datos["email"], "password": datos["password"]},
    )
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Demo SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Providencia 100, Santiago",
            "rut_empresa": "76123456-0",
        },
    )
    assert created.status_code == 201, created.text
    return token, created.json()["id"]

def test_endpoint_doc_empresa_patente(client: TestClient):
    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    pdf = _pdf_texto(_TEXTO_PATENTE)
    r = client.post(
        f"/v1/businesses/{business_id}/documentos/patente",
        headers=h,
        files={"archivo": ("patente.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["verificado"] is True
    assert body["tipo"] == "patente"
    assert body["docs_empresa"]["patente"]["verificado"] is True
    assert body["docs_verificados"] == 1
    assert body["docs_total"] == 11

    assert 0.0 <= float(body["indice_transparencia"]) <= 10.0
    assert 0 <= int(body["indice_pct"]) <= 100

def test_endpoint_doc_empresa_escaneo_422(client: TestClient):
    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = BytesIO()
    writer.write(buf)
    r = client.post(
        f"/v1/businesses/{business_id}/documentos/patente",
        headers=h,
        files={"archivo": ("scan.pdf", buf.getvalue(), "application/pdf")},
    )
    assert r.status_code == 422

def test_endpoint_doc_empresa_tipo_invalido(client: TestClient):
    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        f"/v1/businesses/{business_id}/documentos/foo",
        headers=h,
        files={"archivo": ("x.pdf", _pdf_texto(_TEXTO_PATENTE), "application/pdf")},
    )
    assert r.status_code == 422

def test_endpoint_inicio_actividades_sin_firma_422(client: TestClient):
    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    r = client.post(
        f"/v1/businesses/{business_id}/documentos/inicio_actividades",
        headers=h,
        files={
            "archivo": (
                "inicio.pdf",
                _pdf_texto(_TEXTO_SII),
                "application/pdf",
            )
        },
    )
    assert r.status_code == 422

def test_endpoint_inicio_actividades_pades_ok(client: TestClient, vault_pades):
    from tests.helpers_pades import firmar_pdf_pades, pdf_con_texto

    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    signed = firmar_pdf_pades(
        pdf_con_texto(_TEXTO_SII),
        common_name="Servicio de Impuestos Internos",
        leaf_cert_pem=vault_pades["leaf_pem"],
        leaf_key_pem=vault_pades["leaf_key"],
    )
    r = client.post(
        f"/v1/businesses/{business_id}/documentos/inicio_actividades",
        headers=h,
        files={"archivo": ("inicio.pdf", signed, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["verificado"] is True
    assert body["verificado_criptograficamente"] is True
    assert body["entidad_emisora"] == "SII"
    assert body["sha256_hash"]

def test_endpoint_revocar_doc_empresa(client: TestClient):
    token, business_id = _crear_proveedor(client)
    h = {"Authorization": f"Bearer {token}"}
    pdf = _pdf_texto(_TEXTO_PATENTE)
    up = client.post(
        f"/v1/businesses/{business_id}/documentos/patente",
        headers=h,
        files={"archivo": ("patente.pdf", pdf, "application/pdf")},
    )
    assert up.status_code == 201, up.text
    assert up.json()["docs_empresa"]["patente"]["vence_en"]

    rev = client.delete(
        f"/v1/businesses/{business_id}/documentos/patente",
        headers=h,
    )
    assert rev.status_code == 200, rev.text
    body = rev.json()
    assert body["verificado"] is False
    assert "patente" not in (body.get("docs_empresa") or {})
    assert body["docs_verificados"] == 0
    assert "revocado" in body["motivo"].lower()

    rep = client.get(f"/v1/businesses/{business_id}/reputation")
    assert rep.status_code == 200
    assert "patente" not in (rep.json().get("docs_empresa") or {})

