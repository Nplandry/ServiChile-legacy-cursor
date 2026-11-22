import uuid

from fastapi.testclient import TestClient

from app.dominio.docs_empresa import TIPOS_DOC_EMPRESA, docs_empresa_desde_raw
from app.dominio.transparencia.valoracion import calcular_indice

from app.infraestructura.persistencia.modelos import (
    EntidadNegocio,
    MetricasReputacionNegocio,
)

def test_indice_en_rango_0_a_10():
    vacio = calcular_indice(docs=None)
    completo = calcular_indice(
        docs=docs_empresa_desde_raw({t: {"verificado": True} for t in TIPOS_DOC_EMPRESA})
    )
    assert vacio == 0.0
    assert completo == 10.0
    assert 0.0 <= vacio <= 10.0
    assert 0.0 <= completo <= 10.0

def test_verificacion_sube_el_indice():
    sin_docs = calcular_indice(docs={})
    con_docs = calcular_indice(
        docs=docs_empresa_desde_raw({TIPOS_DOC_EMPRESA[0]: {"verificado": True}})
    )
    assert con_docs > sin_docs

def test_sin_resenas_no_invalida_el_indice():
    indice = calcular_indice(docs=None)
    assert 0.0 <= indice <= 10.0

def _crear_negocio(
    session_factory, *, claimed=False, metricas=True, **kwargs
) -> uuid.UUID:

    with session_factory() as s:

        negocio = EntidadNegocio(
            nombre=kwargs.get("nombre", "Proveedor TI Central"),
            categoria=kwargs.get("categoria", "tecnologia"),
            latitud=-33.45,
            longitud=-70.66,
            direccion=kwargs.get("direccion", "Av. Siempre Viva 100"),
            descripcion=kwargs.get("descripcion", "Un lugar de prueba."),
            servicios=kwargs.get("servicios") or [],
            industrias=kwargs.get("industrias") or [],
            contrataciones=kwargs.get("contrataciones") or [],
            monto=kwargs.get("monto"),
            plazo=kwargs.get("plazo"),
            referencias=kwargs.get("referencias") or [],
            requiere_nivel=kwargs.get("requiere_nivel", 1),
            is_claimed=claimed,
        )

        s.add(negocio)

        s.flush()

        if metricas:

            s.add(
                MetricasReputacionNegocio(
                    business_id=negocio.id,
                    google_rating_avg=kwargs.get("rating", 4.2),
                    google_reviews_count=kwargs.get("reviews", 150),
                    final_score=kwargs.get("final_score", 7.5),
                )
            )

        s.commit()

        return negocio.id

def test_reputacion_publica_no_requiere_sesion(client: TestClient, session_factory):

    bid = _crear_negocio(session_factory)

    r = client.get(f"/v1/businesses/{bid}/reputation")

    assert r.status_code == 200, r.text

    cuerpo = r.json()

    assert cuerpo["business_id"] == str(bid)

    assert "indice_transparencia" in cuerpo
    assert 0.0 <= float(cuerpo["indice_transparencia"]) <= 10.0
    assert cuerpo["docs_verificados"] == 0
    assert cuerpo["docs_total"] == len(TIPOS_DOC_EMPRESA)
    assert cuerpo["google_rating_avg"] == 4.2
    assert cuerpo["google_reviews_count"] == 150
    assert len(cuerpo["observables"]) == 3
    assert cuerpo["docs_empresa"] is None

def test_reputacion_sin_sello_verificado(client: TestClient, session_factory):

    bid = _crear_negocio(session_factory, claimed=False)

    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert "is_verified_profile" not in cuerpo
    assert "estado_perfil" not in cuerpo

    assert "No constituye un juicio" in cuerpo["descargo"]
    assert "reviews" not in cuerpo and "comentarios" not in cuerpo

def test_reputacion_docs_solo_flags_publicos(client: TestClient, session_factory):
    with session_factory() as s:
        negocio = EntidadNegocio(
            nombre="Docs Publicos SpA",
            categoria="tecnologia",
            latitud=-33.45,
            longitud=-70.66,
            docs_empresa={
                "patente": {
                    "verificado": True,
                    "verificado_en": "2026-01-01T00:00:00+00:00",
                    "score": 92,
                    "sha256_hash": "abc" * 20,
                    "glosa": "secreto",
                    "senales": ["interno"],
                }
            },
        )
        s.add(negocio)
        s.flush()
        s.add(MetricasReputacionNegocio(business_id=negocio.id, final_score=5.0))
        s.commit()
        bid = negocio.id

    publico = client.get(f"/v1/businesses/{bid}/reputation").json()
    assert publico["docs_empresa"] is None
    assert len(publico["observables"]) == 3

def test_reputacion_negocio_inexistente_da_404(client: TestClient):

    r = client.get(f"/v1/businesses/{uuid.uuid4()}/reputation")

    assert r.status_code == 404

def test_reputacion_sin_metricas_calcula_al_vuelo(client: TestClient, session_factory):

    bid = _crear_negocio(session_factory, metricas=False)

    cuerpo = client.get(f"/v1/businesses/{bid}/reputation").json()

    assert cuerpo["indice_transparencia"] == 0.0
    assert cuerpo["indice_pct"] == 0

def test_crear_empresa_persona_da_403(client: TestClient, token: str):

    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Persona SpA",
            "categoria": "tecnologia",
            "direccion": "Calle 1",
        },
    )

    assert r.status_code == 403

def test_crear_empresa_queda_del_titular(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    banner = "https://cdn.ejemplo.cl/banner-pyme.jpg"

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Nueva Pyme SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 100",
            "telefono": "+56 9 1111 2222",
            "imagen_url": banner,
            "logo_url": "https://cdn.ejemplo.cl/logo-pyme.png",
        },
    )

    assert r.status_code == 201, r.text

    cuerpo = r.json()

    assert cuerpo["nombre"] == "Nueva Pyme SpA"

    assert cuerpo["direccion"] == "Providencia 100"

    assert cuerpo["is_claimed"] is True

    assert "is_verified_profile" not in cuerpo

    assert cuerpo["imagen_url"] == banner

    assert cuerpo["logo_url"] == "https://cdn.ejemplo.cl/logo-pyme.png"

    assert cuerpo["latitud"] is not None and cuerpo["longitud"] is not None
    assert -56.0 <= float(cuerpo["latitud"]) <= -17.0
    assert -76.0 <= float(cuerpo["longitud"]) <= -66.0

    assert 0.0 <= float(cuerpo["indice_transparencia"]) <= 10.0
    assert 0 <= int(cuerpo["indice_pct"]) <= 100

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert any((n["id"] == cuerpo["id"] for n in mias.json()))

def test_telefono_empresa_debe_empezar_con_mas_56(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    base = {
        "nombre": "Tel SpA",
        "categoria": "tecnologia",
        "direccion": "Providencia 10",
    }
    assert (
        client.post(
            "/v1/businesses", headers=h, json={**base, "telefono": "9 1234 5678"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/businesses", headers=h, json={**base, "telefono": "56912345678"}
        ).status_code
        == 422
    )
    r = client.post(
        "/v1/businesses", headers=h, json={**base, "telefono": "+56912345678"}
    )
    assert r.status_code == 201, r.text
    assert r.json()["telefono"] == "+56 9 1234 5678"

def test_actualizar_datos_empresa_refresca_ficha(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Editar SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 1",
            "rut_empresa": "76.123.456-0",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    ok = client.patch(
        f"/v1/businesses/{bid}",
        headers=h,
        json={
            "nombre": "Editada SpA",
            "categoria": "industria",
            "direccion": "Las Condes 50",
            "telefono": "+56 9 8765 4321",
            "sitio_web": "https://editada.cl",
            "rut_empresa": "76.123.456-0",
        },
    )
    assert ok.status_code == 200, ok.text
    cuerpo = ok.json()
    assert cuerpo["nombre"] == "Editada SpA"
    assert cuerpo["categoria"] == "industria"
    assert cuerpo["direccion"] == "Las Condes 50"
    assert cuerpo["telefono"] == "+56 9 8765 4321"
    assert cuerpo["sitio_web"] == "https://editada.cl"
    assert cuerpo["rut_empresa"] == "76123456-0"

def test_crear_empresa_con_rut_repetido_da_409(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    cuerpo = {
        "nombre": "Primera SpA",
        "categoria": "tecnologia",
        "direccion": "Providencia 1",
        "rut_empresa": "76.123.456-0",
    }
    alta = client.post("/v1/businesses", headers=h, json=cuerpo)
    assert alta.status_code == 201, alta.text

    repetida = client.post(
        "/v1/businesses",
        headers=h,
        json={**cuerpo, "nombre": "Otra SpA", "direccion": "Las Condes 2"},
    )
    assert repetida.status_code == 409, repetida.text
    assert repetida.json()["detail"] == "Este RUT de empresa ya está registrado."

    mias = client.get("/v1/businesses/mias", headers=h)
    assert mias.status_code == 200
    assert [n["nombre"] for n in mias.json()] == ["Primera SpA"]

def test_actualizar_rut_empresa_habilita_consulta(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Rut Pendiente SpA",
            "categoria": "tecnologia",
            "direccion": "Las Condes 10",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    assert r.json().get("rut_empresa") in (None, "")

    bad = client.patch(
        f"/v1/businesses/{bid}/rut",
        headers=h,
        json={"rut_empresa": "no-es-rut"},
    )
    assert bad.status_code == 422

    ok = client.patch(
        f"/v1/businesses/{bid}/rut",
        headers=h,
        json={"rut_empresa": "76.123.456-0"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["rut_empresa"] == "76123456-0"

    mias = client.get("/v1/businesses/mias", headers=h)
    assert mias.status_code == 200
    mia = next(n for n in mias.json() if n["id"] == bid)
    assert mia["rut_empresa"] == "76123456-0"

def test_crear_empresa_banner_invalido_da_422(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Sin Banner SpA",
            "categoria": "industria",
            "direccion": "Av. Central 1",
            "imagen_url": "ftp://no-vale.cl/x.jpg",
        },
    )

    assert r.status_code == 422

def test_crear_empresa_banner_http_se_upgradea_a_https(
    client: TestClient, token_empresa: str
):
    h = {"Authorization": f"Bearer {token_empresa}"}
    r = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Banner Http SpA",
            "categoria": "industria",
            "direccion": "Av. Central 2",
            "imagen_url": "http://cdn.ejemplo.cl/banner.jpg",
            "logo_url": "http://cdn.ejemplo.cl/logo.png",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["imagen_url"] == "https://cdn.ejemplo.cl/banner.jpg"
    assert cuerpo["logo_url"] == "https://cdn.ejemplo.cl/logo.png"

def test_crear_empresa_sin_direccion_da_422(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.post(
        "/v1/businesses",
        headers=h,
        json={"nombre": "Sin Direccion SpA", "categoria": "industria"},
    )

    assert r.status_code == 422

def test_crear_empresa_requiere_sesion(client: TestClient):

    r = client.post(
        "/v1/businesses",
        json={
            "nombre": "Sin Sesion SpA",
            "categoria": "industria",
            "direccion": "Calle 1",
        },
    )

    assert r.status_code == 401

def test_eliminar_empresa_la_borra(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    creada = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Pyme Temporal SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Temporal 10",
        },
    )

    assert creada.status_code == 201

    bid = creada.json()["id"]

    r = client.delete(f"/v1/businesses/{bid}", headers=h)

    assert r.status_code == 204

    mias = client.get("/v1/businesses/mias", headers=h)

    assert mias.status_code == 200

    assert all((n["id"] != bid for n in mias.json()))

    publico = client.get("/v1/businesses")

    assert all((n["id"] != bid for n in publico.json()))

    assert client.get(f"/v1/businesses/{bid}/reputation").status_code == 404

def test_eliminar_empresa_ajena_da_403(
    client: TestClient, session_factory, token_empresa: str
):

    bid = _crear_negocio(session_factory, claimed=True)

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.delete(f"/v1/businesses/{bid}", headers=h)

    assert r.status_code == 403

def test_eliminar_empresa_inexistente_da_404(client: TestClient, token_empresa: str):

    h = {"Authorization": f"Bearer {token_empresa}"}

    r = client.delete(f"/v1/businesses/{uuid.uuid4()}", headers=h)

    assert r.status_code == 404

def test_listado_publico_devuelve_negocios_con_indice(
    client: TestClient, session_factory
):

    _crear_negocio(session_factory, nombre="FitHouse Gym", categoria="tecnologia")

    r = client.get("/v1/businesses")

    assert r.status_code == 200, r.text

    cuerpo = r.json()

    assert len(cuerpo) == 1

    item = cuerpo[0]

    assert item["nombre"] == "FitHouse Gym"

    assert item["categoria"] == "tecnologia"

    assert item["indice_transparencia"] == 7.5
    assert item["indice_pct"] == 75

    assert item["latitud"] == -33.45 and item["longitud"] == -70.66

    assert item["requiere_nivel"] == 1

    assert item["cta_texto"] == "Ver ficha de transparencia"

    assert item["logo_texto"]

    assert item["imagen_url"]

    assert "google_reviews_count" not in item
    assert "docs_empresa" not in item
    assert "rut_empresa" not in item
    assert "telefono" not in item
    assert "sitio_web" not in item

def test_listado_filtra_por_categoria(client: TestClient, session_factory):

    _crear_negocio(session_factory, nombre="SaaS Uno", categoria="tecnologia")

    _crear_negocio(
        session_factory,
        nombre="Maestranza Dos",
        categoria="industria",
        requiere_nivel=2,
    )

    r = client.get("/v1/businesses", params={"categoria": "industria"})

    assert r.status_code == 200

    cuerpo = r.json()

    assert len(cuerpo) == 1

    assert cuerpo[0]["categoria"] == "industria"

    assert cuerpo[0]["requiere_nivel"] == 2

def test_listado_busca_por_nombre_o_direccion(client: TestClient, session_factory):

    _crear_negocio(
        session_factory,
        nombre="Consultora Norte",
        categoria="servicios-profesionales",
        direccion="Santa Isabel 512",
    )

    _crear_negocio(
        session_factory,
        nombre="SaaS Central",
        categoria="tecnologia",
        direccion="Providencia 1420",
    )

    assert len(client.get("/v1/businesses", params={"q": "Norte"}).json()) == 1

    assert len(client.get("/v1/businesses", params={"q": "Providencia"}).json()) == 1

    assert (
        len(client.get("/v1/businesses", params={"q": "nada-que-coincide"}).json()) == 0
    )

def test_listado_vacio_sin_negocios(client: TestClient):

    assert client.get("/v1/businesses").json() == []

def test_listado_sin_metricas_calcula_indice_minimo(
    client: TestClient, session_factory
):

    _crear_negocio(session_factory, metricas=False)

    cuerpo = client.get("/v1/businesses").json()

    assert len(cuerpo) == 1

    assert cuerpo[0]["indice_transparencia"] == 0.0
    assert cuerpo[0]["indice_pct"] == 0

def test_oferta_se_guarda_y_filtra_el_mapa(client: TestClient, token_empresa: str, session_factory):
    h = {"Authorization": f"Bearer {token_empresa}"}
    oferta = {
        "servicios": ["Bodega", "última milla"],
        "industrias": ["mineria", "retail"],
        "contrataciones": ["factura-electronica", "licitacion-oc"],
        "monto": "alto",
        "plazo": "en-el-dia",
        "referencias": ["Falabella", "Codelco"],
    }
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Logística Sur SpA",
            "categoria": "logistica",
            "direccion": "Ruta 5 Sur 100",
            "rut_empresa": "76.123.456-0",
            **oferta,
        },
    )
    assert alta.status_code == 201, alta.text
    cuerpo = alta.json()
    assert cuerpo["servicios"] == ["Bodega", "última milla"]
    assert cuerpo["industrias"] == ["mineria", "retail"]
    assert cuerpo["contrataciones"] == ["factura-electronica", "licitacion-oc"]
    assert cuerpo["monto"] == "alto"
    assert cuerpo["plazo"] == "en-el-dia"
    assert cuerpo["referencias"] == ["Falabella", "Codelco"]

    _crear_negocio(
        session_factory,
        nombre="Otra Industria",
        categoria="industria",
        servicios=["Mantención"],
        industrias=["salud"],
        monto="bajo",
        plazo="24-48h",
        referencias=["Clínica Norte"],
    )

    assert len(client.get("/v1/businesses", params={"q": "bodega"}).json()) == 1
    assert len(client.get("/v1/businesses", params={"q": "Falabella"}).json()) == 1
    retail = client.get("/v1/businesses", params={"industria": "retail"}).json()
    assert [n["nombre"] for n in retail] == ["Logística Sur SpA"]
    factura = client.get(
        "/v1/businesses", params={"contratacion": "factura-electronica"}
    ).json()
    assert len(factura) == 1
    assert client.get("/v1/businesses", params={"monto": "alto"}).json()[0]["nombre"] == (
        "Logística Sur SpA"
    )
    assert client.get("/v1/businesses", params={"plazo": "24-48h"}).json()[0]["nombre"] == (
        "Otra Industria"
    )

    invalida = client.get("/v1/businesses", params={"industria": "astronomia"})
    assert invalida.status_code == 422
    assert isinstance(invalida.json()["detail"], str)

    larga = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Tags SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 9",
            "servicios": ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete"],
        },
    )
    assert larga.status_code == 422

def test_actualizar_oferta_reemplaza_lo_declarado(client: TestClient, token_empresa: str):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Oferta SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 2",
            "rut_empresa": "76.123.456-0",
            "servicios": ["SaaS"],
            "monto": "bajo",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    ok = client.patch(
        f"/v1/businesses/{bid}",
        headers=h,
        json={
            "nombre": "Oferta SpA",
            "categoria": "tecnologia",
            "direccion": "Providencia 2",
            "rut_empresa": "76.123.456-0",
            "servicios": ["Datos"],
            "industrias": ["sector-publico"],
            "monto": "medio",
            "plazo": "menos-2h",
            "referencias": ["Ministerio"],
        },
    )
    assert ok.status_code == 200, ok.text
    cuerpo = ok.json()
    assert cuerpo["servicios"] == ["Datos"]
    assert cuerpo["industrias"] == ["sector-publico"]
    assert cuerpo["monto"] == "medio"
    assert cuerpo["plazo"] == "menos-2h"
    assert cuerpo["referencias"] == ["Ministerio"]
    assert cuerpo["contrataciones"] == []
