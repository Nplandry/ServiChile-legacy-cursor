import os

os.environ["JWT_SECRET"] = "test-secret-de-al-menos-32-caracteres-xx"
os.environ["APP_ENV"] = "test"
os.environ["SERVICHILE_ALLOW_MEMORIA_PASARELA"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import dependencias
from app.configuracion import obtener_configuracion
from app.infraestructura.biometria_fs import AlmacenamientoBiometriaLocal
from app.infraestructura.cedula_fs import AlmacenamientoCedulaLocal
from app.infraestructura.cedula_ocr import AnalizadorCedulaOcr, LectorOcrFijo
from app.infraestructura.cedula_vision import ComparadorRostrosFijo
from app.infraestructura.persistencia.modelos import Base, obtener_sesion
from app.infraestructura.limite_solicitudes import LimiteSolicitudesMemoria
from app.ensamblado.evaluador import obtener_adaptador_evaluador
from app.principal import app

obtener_configuracion.cache_clear()
obtener_adaptador_evaluador.cache_clear()

_TEXTO_OCR_CEDULA = """
CÉDULA DE REPÚBLICA DE CHILE
IDENTIDAD SERVICIO DE REGISTRO CIVIL E IDENTIFICACIÓN
APELLIDOS
GONZALEZ
PEREZ
NOMBRES
MARIA
NACIONALIDAD CHILENA
FECHA DE NACIMIENTO 15 ENE 1990
FECHA DE EMISION FECHA DE VENCIMIENTO
27 MAYO 2025 15 ENE 2032
RUN 12.345.678-5
"""

@pytest.fixture
def biometria_dir(tmp_path):
    return tmp_path / "biometria"

@pytest.fixture
def cedula_dir(tmp_path):
    return tmp_path / "cedulas"

@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Base.metadata.tables[t]
            for t in (
                "usuarios",
                "usuario_xp_eventos",
                "perfiles",
                "business_entities",
                "business_reputation_metrics",
                "trabajos",
                "pades_document_hashes",
                "correo_oauth",
                "mensajes_correo",
                "compras_informe",
                "compras_publicacion",
            )
        ],
    )
    return sessionmaker(bind=engine, expire_on_commit=False)

@pytest.fixture
def vault_pades(tmp_path):

    from tests.helpers_pades import crear_ca_y_hoja, vault_con_raiz_prueba

    root_pem, leaf_pem, leaf_key = crear_ca_y_hoja(
        leaf_cn="Servicio de Impuestos Internos",
        leaf_org="Servicio de Impuestos Internos",
    )
    path = vault_con_raiz_prueba(tmp_path / "ca_test.pem", root_pem)
    return {
        "path": str(path),
        "root_pem": root_pem,
        "leaf_pem": leaf_pem,
        "leaf_key": leaf_key,
    }

@pytest.fixture
def client(session_factory, biometria_dir, cedula_dir, vault_pades):
    from app.infraestructura.pdf_antecedentes import AnalizadorPdfAntecedentes
    from app.infraestructura.pdf_docs_empresa import AnalizadorPdfDocEmpresa
    from app.infraestructura.trust_vault import invalidar_cache_confianza

    def _session():
        with session_factory() as s:
            yield s

    limiter = LimiteSolicitudesMemoria()
    bio = AlmacenamientoBiometriaLocal(biometria_dir)
    ced = AlmacenamientoCedulaLocal(cedula_dir)
    analizador = AnalizadorCedulaOcr(
        LectorOcrFijo(_TEXTO_OCR_CEDULA), ComparadorRostrosFijo(0.9)
    )
    ca = vault_pades["path"]
    invalidar_cache_confianza()
    ant = AnalizadorPdfAntecedentes(ca)
    docs = AnalizadorPdfDocEmpresa(ca)

    app.dependency_overrides[obtener_sesion] = _session
    app.dependency_overrides[dependencias.obtener_limite_solicitudes] = lambda: limiter
    app.dependency_overrides[dependencias.obtener_almacenamiento_biometria] = lambda: bio
    app.dependency_overrides[dependencias.obtener_almacenamiento_cedula] = lambda: ced
    app.dependency_overrides[dependencias.obtener_analizador_cedula] = lambda: analizador
    app.dependency_overrides[dependencias.obtener_analizador_antecedentes] = lambda: ant
    app.dependency_overrides[dependencias.obtener_analizador_docs_empresa] = lambda: docs
    from app.infraestructura.verificacion import MuestraVerificadorRut

    app.dependency_overrides[dependencias.obtener_verificador_rut] = (
        lambda: MuestraVerificadorRut()
    )

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    invalidar_cache_confianza()

@pytest.fixture
def token(client: TestClient) -> str:
    datos = {
        "email": "Maria@Servichile.cl",
        "nombre": "María González",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "persona"},
    }
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    r = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    )
    return r.json()["access_token"]

@pytest.fixture
def token_empresa(client: TestClient) -> str:
    datos = {
        "email": "Empresa@Servichile.cl",
        "nombre": "Proveedor Demo SpA",
        "password": "clave-segura-123",
        "perfil": {"tipo_cuenta": "proveedor"},
    }
    assert client.post("/v1/auth/registro", json=datos).status_code == 201
    r = client.post(
        "/v1/auth/login", json={"email": datos["email"], "password": datos["password"]}
    )
    return r.json()["access_token"]
