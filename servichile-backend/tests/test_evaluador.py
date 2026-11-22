from uuid import uuid4

from app.dominio.entidades import Negocio
from app.dominio.transparencia.evaluador.parametros import IDS_ESTADO, PARAMETROS
from app.infraestructura.evaluador.adaptador import AdaptadorEvaluador, ConfiguracionEvaluador

def _negocio(**kwargs) -> Negocio:
    base = dict(
        id=uuid4(),
        nombre="Demo SpA",
        categoria="tecnologia",
        latitud=None,
        longitud=None,
        direccion=None,
        descripcion=None,
        imagen_url=None,
        logo_url=None,
        requiere_nivel=1,
        is_claimed=True,
        telefono=None,
        sitio_web=None,
        rut_empresa=None,
        docs_empresa={},
    )
    base.update(kwargs)
    return Negocio(**base)

def test_evaluador_test_sin_campos_deja_ceros():
    svc = AdaptadorEvaluador(ConfiguracionEvaluador(app_env="test"))
    res = svc.evaluar(_negocio())
    assert len(res.parametros) == len(PARAMETROS)
    by_id = {p.id: p for p in res.parametros}
    assert by_id["fis_address"].puntaje == 0.0
    assert by_id["fis_phone"].puntaje == 0.0
    for pid in IDS_ESTADO:
        assert by_id[pid].puntaje == 0.0
    assert by_id["dig_website"].puntaje == 0.0
    assert by_id["cyb_https"].puntaje == 0.0

def test_evaluador_sin_keys_simula_solo_places_y_chilecompra():

    svc = AdaptadorEvaluador(
        ConfiguracionEvaluador(
            app_env="local",
            google_places_api_key="",
            chilecompra_ticket="",
        )
    )
    res = svc.evaluar(
        _negocio(
            direccion="Av. Providencia 100, Santiago",
            telefono="+56911111111",
            rut_empresa="76123456-0",
        )
    )
    by_id = {p.id: p for p in res.parametros}
    assert by_id["fis_address"].puntaje and by_id["fis_address"].puntaje > 0
    assert by_id["fis_phone"].puntaje and by_id["fis_phone"].puntaje > 0
    assert by_id["est_proveedor"].puntaje and by_id["est_proveedor"].puntaje > 0
    assert res.metadatos.get("places", {}).get("modo") == "fijos"
    assert res.metadatos.get("chilecompra", {}).get("modo") == "fijos"
    assert res.metadatos.get("rastreador_web", {}).get("omitido") is True

def test_evaluador_test_con_ficha_completa_usa_fijos():
    svc = AdaptadorEvaluador(ConfiguracionEvaluador(app_env="test"))
    res = svc.evaluar(
        _negocio(
            direccion="Av. Providencia 100, Santiago",
            telefono="+56911111111",
            sitio_web="https://ejemplo.cl",
            rut_empresa="76123456-0",
        )
    )
    by_id = {p.id: p for p in res.parametros}
    assert by_id["fis_address"].puntaje and by_id["fis_address"].puntaje > 0
    assert by_id["est_proveedor"].puntaje and by_id["est_proveedor"].puntaje > 0
    assert by_id["dig_website"].puntaje == 100.0
    assert res.puntaje_global is not None
    assert {o.grupo for o in res.a_observables()} >= {
        "ciber",
        "contractual",
        "operativa",
        "legal",
    }
    assert res.metadatos.get("rastreador_web", {}).get("modo") == "fijos"

def test_reputacion_incluye_observables_evaluador(client, token_empresa):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Rater Demo SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Apoquindo 3000, Las Condes",
            "sitio_web": "https://rater-demo.cl",
            "rut_empresa": "76999888-5",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]

    publico = client.get(f"/v1/businesses/{bid}/reputation")
    assert publico.status_code == 200
    pub = publico.json()
    assert {o["id"] for o in pub["observables"]} == {
        "doc_patente",
        "fis_reviews",
        "cyb_referrer",
    }
    assert pub["observables_restantes"] >= 31
    assert pub["docs_empresa"] is None

    r = client.get(
        f"/v1/businesses/{bid}/reputation",
        headers={"Authorization": f"Bearer {token_empresa}"},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["observables"]) >= len(PARAMETROS)
    ids = {o["id"] for o in cuerpo["observables"]}
    assert "fis_address" in ids and "est_proveedor" in ids and "cyb_https" in ids

def test_reputacion_bearer_sin_compra_oculta_observables(
    client, token_empresa, token
):
    alta = client.post(
        "/v1/businesses",
        headers={"Authorization": f"Bearer {token_empresa}"},
        json={
            "nombre": "Privada SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Las Condes 100, Santiago",
            "sitio_web": "https://privada-demo.cl",
            "rut_empresa": "76777666-K",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]

    ajeno = client.get(
        f"/v1/businesses/{bid}/reputation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ajeno.status_code == 200
    cuerpo_ajeno = ajeno.json()
    assert {o["id"] for o in cuerpo_ajeno["observables"]} == {
        "doc_patente",
        "fis_reviews",
        "cyb_referrer",
    }
    assert cuerpo_ajeno["observables_restantes"] >= 31
    assert cuerpo_ajeno["docs_empresa"] is None

def test_refresco_evaluador_titular_refresca_indice(client, token_empresa):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Scan SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Providencia 100, Santiago",
            "sitio_web": "https://scan-demo.cl",
            "rut_empresa": "76888777-2",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    r = client.post(f"/v1/businesses/{bid}/rater-refresh", headers=h)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["business_id"] == bid
    assert len(cuerpo["observables"]) >= len(PARAMETROS)
    assert "descargo" in cuerpo

def test_refresco_evaluador_ajeno_da_403(client, token_empresa, token):
    h = {"Authorization": f"Bearer {token_empresa}"}
    alta = client.post(
        "/v1/businesses",
        headers=h,
        json={
            "nombre": "Ajeno Scan SpA",
            "categoria": "tecnologia",
            "direccion": "Av. Las Condes 1, Las Condes",
        },
    )
    assert alta.status_code == 201, alta.text
    bid = alta.json()["id"]
    r = client.post(
        f"/v1/businesses/{bid}/rater-refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403

def test_conservar_sitio_previa_no_pisa_ciber_contractual():
    from uuid import uuid4

    from app.dominio.entidades import Metricas, ObservableSenal
    from app.servicios.negocio import ServicioNegocio

    bid = uuid4()
    metricas = Metricas(
        business_id=bid,
        observables=[
            {
                "id": "cyb_https",
                "etiqueta": "HTTPS habilitado",
                "detalle": "rastreador_web",
                "score": 100,
                "peso": "1.2",
                "grupo": "ciber",
                "razones": [],
            },
            {
                "id": "con_privacy",
                "etiqueta": "Tiene política de privacidad",
                "detalle": "rastreador_web",
                "score": 100,
                "peso": "1.4",
                "grupo": "contractual",
                "razones": [],
            },
        ],
    )
    nuevos = [
        ObservableSenal(
            id="cyb_https",
            etiqueta="HTTPS habilitado",
            detalle="",
            score=0,
            peso="1.2",
            grupo="ciber",
        ),
        ObservableSenal(
            id="con_privacy",
            etiqueta="Tiene política de privacidad",
            detalle="",
            score=0,
            peso="1.4",
            grupo="contractual",
        ),
        ObservableSenal(
            id="fis_rating",
            etiqueta="Nota",
            detalle="",
            score=80,
            peso="1.0",
            grupo="operativa",
        ),
    ]
    out = ServicioNegocio._conservar_sitio_previa(metricas, nuevos)
    by_id = {o.id: o for o in out}
    assert by_id["cyb_https"].score == 100
    assert by_id["con_privacy"].score == 100
    assert by_id["fis_rating"].score == 80
