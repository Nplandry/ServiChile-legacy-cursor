import uuid

import pytest
from fastapi.testclient import TestClient

from app.infraestructura.persistencia.modelos import (
    EntidadNegocio,
    MetricasReputacionNegocio,
)

def _cuenta(client: TestClient, email: str) -> dict:
    assert (
        client.post(
            "/v1/auth/registro",
            json={
                "email": email,
                "nombre": "Comprador",
                "password": "clave-segura-123",
                "perfil": {"tipo_cuenta": "persona"},
            },
        ).status_code
        == 201
    )
    token = client.post(
        "/v1/auth/login", json={"email": email, "password": "clave-segura-123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def _negocio(session_factory, nombre="Gearlabs"):
    with session_factory() as s:
        negocio = EntidadNegocio(
            nombre=nombre, categoria="tecnologia", rut_empresa="76123456-0"
        )
        s.add(negocio)
        s.flush()
        s.add(MetricasReputacionNegocio(business_id=negocio.id, final_score=3.0))
        s.commit()
        return negocio.id

def test_catalogo_pago_informe(client: TestClient):
    from app.dominio.pago_informe import PRECIO_INFORME_CLP

    r = client.get("/v1/pagos/informe/catalogo")
    assert r.status_code == 200, r.text
    assert r.json()["monto"] == PRECIO_INFORME_CLP
    assert r.json()["moneda"] == "CLP"

def test_precios_solo_en_dominio_sin_override_env(monkeypatch):

    from app.configuracion import Configuracion, obtener_configuracion
    from app.dominio.pago_informe import PRECIO_INFORME_CLP
    from app.dominio.pago_publicacion import PRECIO_PUBLICACION_CLP

    assert "pagos_informe_monto" not in Configuracion.model_fields
    assert "pagos_publicacion_monto" not in Configuracion.model_fields

    monkeypatch.setenv("PAGOS_INFORME_MONTO", "12345")
    monkeypatch.setenv("PAGOS_PUBLICACION_MONTO", "6789")
    obtener_configuracion.cache_clear()
    try:

        from fastapi.testclient import TestClient

        from app.principal import app

        with TestClient(app) as client:
            inf = client.get("/v1/pagos/informe/catalogo")
            pub = client.get("/v1/pagos/publicacion/catalogo")
        assert inf.status_code == 200
        assert pub.status_code == 200
        assert inf.json()["monto"] == PRECIO_INFORME_CLP
        assert pub.json()["monto"] == PRECIO_PUBLICACION_CLP
    finally:
        monkeypatch.delenv("PAGOS_INFORME_MONTO", raising=False)
        monkeypatch.delenv("PAGOS_PUBLICACION_MONTO", raising=False)
        obtener_configuracion.cache_clear()

def test_pago_informe_iniciar_y_confirmar(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory)

    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    )
    assert ini.status_code == 200, ini.text
    data = ini.json()
    assert data["buy_order"].startswith("SCI")
    assert data["token"]
    assert data["url"]
    assert data["monto"] == 9990
    assert "pagos@" in data["reclamo"]["email"]
    assert data["reclamo"]["whatsapp"]

    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": data["token"]},
        headers=headers,
    )
    assert conf.status_code == 200, conf.text
    out = conf.json()
    assert out["autorizado"] is True
    assert out["estado"] == "autorizado"
    assert out["buy_order"] == data["buy_order"]
    assert out["business_id"] == str(bid)

    resumen = client.get("/v1/pagos/informe/resumen", headers=headers)
    assert resumen.status_code == 200
    assert resumen.json()["autorizadas_mes"] >= 1

def test_pago_informe_negocio_inexistente(client: TestClient):
    headers = _cuenta(client, f"pago.miss.{uuid.uuid4().hex[:8]}@example.com")
    r = client.post(
        "/v1/pagos/informe",
        json={"business_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert r.status_code == 404

def test_informe_riesgo_requiere_compra(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.gate.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "GateCo")

    blocked = client.post(
        f"/v1/businesses/{bid}/informe-riesgo", headers=headers
    )
    assert blocked.status_code == 402, blocked.text
    assert blocked.json()["detail"]["codigo"] == "informe_sin_compra"

    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    ).json()
    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200
    assert conf.json()["autorizado"] is True

    ok = client.post(f"/v1/businesses/{bid}/informe-riesgo", headers=headers)
    assert ok.status_code == 200, ok.text

def test_return_url_no_permitida(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.url.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "UrlCo")
    r = client.post(
        "/v1/pagos/informe",
        json={
            "business_id": str(bid),
            "return_url": "https://evil.example/phish?pago=retorno",
        },
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["codigo"] == "return_url_no_permitida"

def test_compra_ajena(client: TestClient, session_factory):
    a = _cuenta(client, f"pago.a.{uuid.uuid4().hex[:8]}@example.com")
    b = _cuenta(client, f"pago.b.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "AjenaCo")
    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=a
    ).json()
    r = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=b,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["codigo"] == "compra_ajena"

def test_doble_confirmar_idempotente(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.dup.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "DupCo")
    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    ).json()
    c1 = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    c2 = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert c1.status_code == 200
    assert c2.status_code == 200
    assert c2.json()["autorizado"] is True
    assert c2.json()["estado"] == "autorizado"

def test_reabrir_informe_ya_comprado(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.re.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "ReopenCo")
    sin = client.get(f"/v1/pagos/informe/acceso/{bid}", headers=headers)
    assert sin.status_code == 402

    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    ).json()
    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200

    otra = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    )
    assert otra.status_code == 409
    assert otra.json()["detail"]["codigo"] == "ya_comprado"

    acceso = client.get(f"/v1/pagos/informe/acceso/{bid}", headers=headers)
    assert acceso.status_code == 200, acceso.text
    assert acceso.json()["autorizado"] is True
    assert acceso.json()["buy_order"] == conf.json()["buy_order"]

def test_print_token_y_verificar(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.print.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "PrintCo")
    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    ).json()
    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200, conf.text
    out = conf.json()
    assert out["autorizado"] is True
    assert out["print_token"]
    assert out["print_token"].count(".") == 2

    ok = client.post(
        "/v1/pagos/informe/verificar-print",
        json={"business_id": str(bid), "print_token": out["print_token"]},
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["autorizado"] is True
    assert ok.json()["buy_order"] == out["buy_order"]

    malo = client.post(
        "/v1/pagos/informe/verificar-print",
        json={
            "business_id": str(bid),
            "print_token": out["print_token"][:-4] + "dead",
        },
        headers=headers,
    )
    assert malo.status_code == 400
    assert malo.json()["detail"]["codigo"] == "print_token_invalido"

def test_recuperar_pago_autorizado(client: TestClient, session_factory):
    headers = _cuenta(client, f"pago.rec.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "RecCo")
    ini = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    ).json()
    conf = client.post(
        "/v1/pagos/informe/confirmar",
        json={"token": ini["token"]},
        headers=headers,
    )
    assert conf.status_code == 200
    rec = client.post(
        "/v1/pagos/informe/recuperar",
        json={"buy_order": conf.json()["buy_order"]},
        headers=headers,
    )
    assert rec.status_code == 200, rec.text
    assert rec.json()["autorizado"] is True
    assert rec.json()["print_token"]

def test_iniciar_crea_token_nuevo_si_habia_pendiente(client: TestClient, session_factory):

    headers = _cuenta(client, f"pago.pend.{uuid.uuid4().hex[:8]}@example.com")
    bid = _negocio(session_factory, "PendCo")
    a = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    )
    assert a.status_code == 200
    orden_a = a.json()["buy_order"]
    token_a = a.json()["token"]
    b = client.post(
        "/v1/pagos/informe", json={"business_id": str(bid)}, headers=headers
    )
    assert b.status_code == 200
    assert b.json()["buy_order"] != orden_a
    assert b.json()["token"] != token_a

    vieja = client.get(f"/v1/pagos/informe/{orden_a}", headers=headers)
    assert vieja.status_code == 200
    assert vieja.json()["estado"] == "anulado"
    nueva = client.get(f"/v1/pagos/informe/{b.json()['buy_order']}", headers=headers)
    assert nueva.status_code == 200
    assert nueva.json()["estado"] == "pendiente"

def test_reconciliar_pendientes_autoriza(session_factory):
    from datetime import datetime, timedelta, timezone

    from app.dominio.pago_informe import ESTADO_AUTORIZADO, ESTADO_PENDIENTE
    from app.infraestructura.correo_plataforma import EnviadorMemoria
    from app.infraestructura.persistencia import modelos as orm
    from app.infraestructura.persistencia.repositorios import (
        RepositorioCompraInforme,
        RepositorioCorreo,
        RepositorioNegocio,
        RepositorioUsuario,
    )
    from app.infraestructura.seguridad.hasheador import HasheadorArgon2
    from app.infraestructura.seguridad.jwt_reporte import JwtReporte
    from app.infraestructura.transbank_webpay import PasarelaWebpayMemoria
    from app.servicios.pago_informe import ServicioPagoInforme
    from app.servicios.radar_comercial import ServicioRadarComercial

    email = f"pago.rec.{uuid.uuid4().hex[:8]}@example.com"
    buy_order = ("SCI" + uuid.uuid4().hex)[:26]
    token = "test-" + buy_order
    with session_factory() as s:
        u = orm.Usuario(
            email=email,
            nombre="Rec",
            password_hash=HasheadorArgon2().hashear("clave-segura-123"),
        )
        s.add(u)
        s.flush()
        neg = orm.EntidadNegocio(
            nombre="RecCo", categoria="tecnologia", rut_empresa="76999888-1"
        )
        s.add(neg)
        s.flush()
        s.add(orm.MetricasReputacionNegocio(business_id=neg.id, final_score=3.0))
        compra = orm.CompraInforme(
            usuario_id=u.id,
            business_id=neg.id,
            buy_order=buy_order,
            monto=9990,
            estado=ESTADO_PENDIENTE,
            token=token,
            creado_en=datetime.now(timezone.utc) - timedelta(seconds=700),
        )
        s.add(compra)
        s.commit()
        uid, bid = u.id, neg.id

    with session_factory() as s:
        pasarela = PasarelaWebpayMemoria(autorizar=True)
        pasarela._tokens[token] = buy_order
        enviador = EnviadorMemoria(simular=True)
        usuarios = RepositorioUsuario(s)
        svc = ServicioPagoInforme(
            RepositorioCompraInforme(s),
            RepositorioNegocio(s),
            pasarela,
            ServicioRadarComercial(
                RepositorioNegocio(s),
                usuarios,
                RepositorioCorreo(s),
                enviador,
                JwtReporte("test-secret-de-al-menos-32-caracteres-xx", 15),
            ),
            return_url="http://localhost:5500/index.html?pago=retorno",
            reclamo_email="pagos@servichile.cl",
            reclamo_whatsapp="+56900000000",
            usuarios=usuarios,
        )
        n = svc.reconciliar_pendientes(min_edad_seg=60, max_edad_seg=7200, limite=10)
        assert n == 1
        c = RepositorioCompraInforme(s).obtener_por_token(token)
        assert c is not None
        assert c.estado == ESTADO_AUTORIZADO
        assert c.usuario_id == uid
        assert c.business_id == bid
        assert len(enviador.enviados) == 1
        assert enviador.enviados[0].destino == email

def _env_prod_base(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    monkeypatch.setenv(
        "PRINT_TOKEN_SECRET", "print-secret-prod-distinto-del-jwt-32c"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PUBLIC_FRONTEND_URL", "https://app.servichile.cl/")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.servichile.cl")

def test_transbank_test_bloqueado_en_production(monkeypatch):
    _env_prod_base(monkeypatch)
    monkeypatch.setenv("TRANSBANK_HOST", "https://webpay3gint.transbank.cl")
    monkeypatch.setenv("TRANSBANK_COMMERCE_CODE", "597055555532")
    monkeypatch.setenv(
        "TRANSBANK_API_KEY",
        "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C",
    )
    from app.configuracion import Configuracion, obtener_configuracion

    obtener_configuracion.cache_clear()
    try:
        raised = False
        try:
            Configuracion()
        except Exception:
            raised = True
        assert raised
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()

def test_front_localhost_bloqueado_en_production(monkeypatch):
    _env_prod_base(monkeypatch)
    monkeypatch.setenv("TRANSBANK_HOST", "https://webpay3g.transbank.cl")
    monkeypatch.setenv("TRANSBANK_COMMERCE_CODE", "597012345678")
    monkeypatch.setenv(
        "TRANSBANK_API_KEY", "prod-key-real-no-es-la-de-integracion-xx"
    )
    monkeypatch.setenv("PUBLIC_FRONTEND_URL", "http://localhost:5500/index.html")
    from app.configuracion import Configuracion, obtener_configuracion

    obtener_configuracion.cache_clear()
    try:
        raised = False
        try:
            Configuracion()
        except Exception:
            raised = True
        assert raised
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()

def test_redis_y_print_secret_obligatorios_en_production(monkeypatch):
    _env_prod_base(monkeypatch)
    monkeypatch.setenv("TRANSBANK_HOST", "https://webpay3g.transbank.cl")
    monkeypatch.setenv("TRANSBANK_COMMERCE_CODE", "597012345678")
    monkeypatch.setenv(
        "TRANSBANK_API_KEY", "prod-key-real-no-es-la-de-integracion-xx"
    )
    from app.configuracion import Configuracion, obtener_configuracion

    obtener_configuracion.cache_clear()
    try:

        with pytest.raises(Exception, match="REDIS_URL"):
            Configuracion(redis_url=None)
        monkeypatch.delenv("PRINT_TOKEN_SECRET", raising=False)
        with pytest.raises(Exception, match="PRINT_TOKEN_SECRET"):
            Configuracion(redis_url="redis://localhost:6379/0", print_token_secret=None)
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()

def test_redis_obligatorio_en_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    from app.configuracion import Configuracion, obtener_configuracion

    obtener_configuracion.cache_clear()
    try:
        with pytest.raises(Exception, match="REDIS_URL"):
            Configuracion(redis_url=None)
    finally:
        monkeypatch.setenv("APP_ENV", "test")
        obtener_configuracion.cache_clear()

def test_require_production_en_cloud(monkeypatch):
    from app.configuracion import Configuracion
    from app.ensamblado.arranque import verificar_entorno_produccion

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://servichile:x@localhost:5432/servichile",
    )
    monkeypatch.setenv("SERVICHILE_REQUIRE_PRODUCTION", "1")
    cfg = Configuracion()
    with pytest.raises(RuntimeError, match="SERVICHILE_REQUIRE_PRODUCTION"):
        verificar_entorno_produccion(cfg)
    monkeypatch.delenv("SERVICHILE_REQUIRE_PRODUCTION", raising=False)

def test_deploy_flag_y_db_remota(monkeypatch):
    from app.configuracion import Configuracion
    from app.ensamblado.arranque import verificar_entorno_produccion

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://servichile:x@localhost:5432/servichile",
    )
    monkeypatch.setenv("SERVICHILE_DEPLOY", "1")
    cfg = Configuracion()
    with pytest.raises(RuntimeError, match="SERVICHILE_DEPLOY"):
        verificar_entorno_produccion(cfg)
    monkeypatch.delenv("SERVICHILE_DEPLOY", raising=False)

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://u:p@db.prod.internal:5432/servichile",
    )
    cfg2 = Configuracion()
    with pytest.raises(RuntimeError, match="DATABASE_URL parece remota"):
        verificar_entorno_produccion(cfg2)

def test_verificar_redis_falla_sin_ping(monkeypatch):
    from app.configuracion import Configuracion
    from app.ensamblado import arranque
    from app.infraestructura.redis_cliente import cliente_redis

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    cfg = Configuracion()

    class _FailRedis:
        def __init__(self, *a, **k):
            pass

        def ping(self):
            raise ConnectionError("down")

    class _FakeRedisMod:
        Redis = _FailRedis

        @staticmethod
        def from_url(*a, **k):
            return _FailRedis()

    import sys

    cliente_redis.cache_clear()
    monkeypatch.setitem(sys.modules, "redis", _FakeRedisMod)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        arranque.verificar_redis(cfg)
    cliente_redis.cache_clear()

def test_permitir_pasarela_memoria_sin_flag_ni_pytest(monkeypatch):
    monkeypatch.delenv("SERVICHILE_ALLOW_MEMORIA_PASARELA", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from app.api.dependencias import permitir_pasarela_memoria

    assert permitir_pasarela_memoria() is False
    monkeypatch.setenv("SERVICHILE_ALLOW_MEMORIA_PASARELA", "1")
    assert permitir_pasarela_memoria() is True

def test_pasarela_memoria_falla_si_no_permitida(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret-de-al-menos-32-caracteres-xx")
    from app.ensamblado import pagos as pagos_ens
    from app.configuracion import obtener_configuracion

    obtener_configuracion.cache_clear()
    pagos_ens.obtener_pasarela_webpay.cache_clear()
    monkeypatch.setattr(pagos_ens, "permitir_pasarela_memoria", lambda: False)
    try:
        with pytest.raises(RuntimeError, match="PasarelaWebpayMemoria"):
            pagos_ens.obtener_pasarela_webpay()
    finally:
        monkeypatch.setenv("SERVICHILE_ALLOW_MEMORIA_PASARELA", "1")
        pagos_ens.obtener_pasarela_webpay.cache_clear()
        obtener_configuracion.cache_clear()
