from __future__ import annotations

import argparse

import sys

from sqlalchemy import inspect, select, text

from sqlalchemy.orm import sessionmaker

from app.dominio.ficha_negocio import IMAGEN_POR_CATEGORIA

from app.dominio.transparencia.valoracion import calcular_indice

from app.infraestructura.persistencia.modelos import (
    EntidadNegocio,
    MetricasReputacionNegocio,
    obtener_motor,
)

from app.tiempo import ahora_utc

_PLANTILLAS = {
    "tecnologia": [
        (
            "SaaS B2B",
            "Plataforma cloud B2B con controles de acceso y bitácora de auditoría.",
        ),
        (
            "Agencia digital",
            "Marketing y performance para cuentas enterprise; manejo de datos de clientes.",
        ),
        ("Consultora TI", "Implementación, soporte y gobierno de sistemas críticos."),
        (
            "Desarrollo a medida",
            "Software a medida, integraciones API y mantenimiento continuo.",
        ),
        (
            "Ciberseguridad MSP",
            "Monitoreo, hardening y respuesta a incidentes para pymes B2B.",
        ),
        (
            "Soporte técnico",
            "Mesa de ayuda y operación de infraestructura para clientes corporativos.",
        ),
    ],
    "industria": [
        ("Maestranza", "Fabricación y reparación industrial para faenas y plantas."),
        (
            "Transporte de carga",
            "Logística de carga pesada y cumplimiento laboral de flota.",
        ),
        (
            "Arriendo de equipos",
            "Arriendo de maquinaria con mantención y seguros vigentes.",
        ),
        ("Aseo industrial", "Servicios de aseo y sanitización en faenas e industrias."),
        (
            "Seguridad privada",
            "Vigilancia y control de acceso con personal acreditado.",
        ),
        (
            "Mantención industrial",
            "Mantención predictiva y correctiva de activos críticos.",
        ),
    ],
    "construccion": [
        (
            "Obras civiles",
            "Subcontrata de obras civiles con foco en seguridad laboral.",
        ),
        ("Electricidad industrial", "Instalaciones eléctricas y certificaciones SEC."),
        ("Climatización", "Montaje y mantención HVAC para edificios e industria."),
        (
            "Montaje estructural",
            "Montaje metálico y estructuras para proyectos mineros.",
        ),
        (
            "Arquitectura e ingeniería",
            "Diseño y dirección de obras con documentación contractual.",
        ),
        (
            "Terminaciones",
            "Terminaciones y especialidades para contratistas principales.",
        ),
    ],
    "servicios-profesionales": [
        (
            "Outsourcing RR.HH.",
            "Administración de nómina y reclutamiento para terceros.",
        ),
        (
            "Contabilidad B2B",
            "Contabilidad, reportes SII y cierre financiero para pymes.",
        ),
        ("Asesoría legal", "Contratos, compliance y acompañamiento en contrataciones."),
        (
            "Consultora laboral",
            "Prevención de riesgos y cumplimiento laboral/previsional.",
        ),
        ("Auditoría interna", "Auditorías de procesos y controles para proveedores."),
        (
            "Gestión de proveedores",
            "Homologación y monitoreo continuo de subcontratistas.",
        ),
    ],
    "logistica": [
        (
            "Flota de carga pesada",
            "Transporte de carga B2B con alta rotación de flotas. Validar vigencia societaria, multas y demandas civiles antes de contratar.",
        ),
        (
            "Courier B2B express",
            "Última milla corporativa. Riesgo de empresas fachada y siniestros; transparencia en segundos.",
        ),
        (
            "Bodegaje y fulfillment",
            "Almacenamiento y picking para e-commerce B2B. Verificar operador, seguros y antecedentes laborales.",
        ),
        (
            "Distribución fría",
            "Cadena de frío para retail e industria. Validar patentes, multas y continuity operativa.",
        ),
        (
            "Courier documental",
            "Mensajería certificada entre sedes. Contrarrestar rotación de proveedores y fraude societario.",
        ),
        (
            "Transporte interurbano",
            "Carga entre regiones. Alto riesgo operativo: robos de carga y accidentes laborales.",
        ),
        (
            "Operador 3PL",
            "Logística integral tercerizada. Homologar vigencia societaria y litigios civiles vigentes.",
        ),
        (
            "Última milla urbana",
            "Entregas densas en ciudad. Clientes necesitan chequear multas y demandas al instante.",
        ),
        (
            "Bodega bonded",
            "Depósito y consolidación de carga. Blindaje ante operadores sin historial verificable.",
        ),
        (
            "Flota liviana B2B",
            "Furgones y utilitarios para cuentas enterprise. Validación rápida de riesgos societarios y laborales.",
        ),
    ],
}

_CIUDADES = [
    ("Santiago", -33.4489, -70.6693),
    ("Providencia", -33.4265, -70.619),
    ("Las Condes", -33.415, -70.58),
    ("Rancagua", -34.1708, -70.7444),
    ("Antofagasta", -23.6509, -70.3975),
    ("Calama", -22.4544, -68.9294),
    ("Valparaíso", -33.0472, -71.6127),
    ("Concepción", -36.8201, -73.0444),
    ("La Serena", -29.9027, -71.2519),
    ("Temuco", -38.7359, -72.5904),
]

_CUOTAS = {
    "tecnologia": 30,
    "industria": 30,
    "construccion": 25,
    "servicios-profesionales": 15,
    "logistica": 10,
}

def _generar_negocios() -> list[dict]:

    out: list[dict] = []

    n = 0

    for categoria, cuota in _CUOTAS.items():

        plantillas = _PLANTILLAS[categoria]

        for i in range(cuota):

            n += 1

            tipo, blurb = plantillas[i % len(plantillas)]

            ciudad, lat0, lng0 = _CIUDADES[(n + i) % len(_CIUDADES)]

            lat = lat0 + (n % 7 - 3) * 0.008

            lng = lng0 + (n % 5 - 2) * 0.008

            out.append(
                {
                    "external_ref": f"seed:b2b-{n:03d}",
                    "nombre": f"{tipo} {ciudad} {n:02d}",
                    "categoria": categoria,
                    "direccion": f"Av. Industrial {100 + n}, {ciudad}",
                    "descripcion": f"{blurb} Operación en {ciudad}. Ficha orientada a transparencia B2B (32 observables).",
                    "imagen_url": IMAGEN_POR_CATEGORIA[categoria],
                    "logo_url": None,
                    "latitud": round(lat, 6),
                    "longitud": round(lng, 6),
                    "requiere_nivel": 1,
                    "google_rating_avg": None,
                    "google_reviews_count": 0,
                }
            )

    return out

NEGOCIOS = _generar_negocios()

COLUMNAS_REQUERIDAS = (
    "direccion",
    "descripcion",
    "requiere_nivel",
    "imagen_url",
    "logo_url",
)

def _indice(n: dict) -> float:

    del n
    return calcular_indice(docs=None)

def _aplicar_negocio(negocio: EntidadNegocio, n: dict) -> None:

    negocio.nombre = n["nombre"]

    negocio.categoria = n["categoria"]

    negocio.direccion = n["direccion"]

    negocio.descripcion = n["descripcion"]

    negocio.imagen_url = n["imagen_url"]

    negocio.logo_url = n["logo_url"]

    negocio.latitud = n["latitud"]

    negocio.longitud = n["longitud"]

    negocio.requiere_nivel = n["requiere_nivel"]

def _aplicar_metricas(negocio: EntidadNegocio, n: dict) -> None:

    if negocio.metricas is None:

        negocio.metricas = MetricasReputacionNegocio(business_id=negocio.id)

    negocio.metricas.google_rating_avg = n["google_rating_avg"]

    negocio.metricas.google_reviews_count = n["google_reviews_count"]

    negocio.metricas.final_score = _indice(n)

    negocio.metricas.rater_escaneado_en = ahora_utc()

def _verificar_esquema(engine) -> None:

    insp = inspect(engine)

    if not insp.has_table("business_entities"):

        raise RuntimeError(
            "Falta la tabla business_entities. Corra db/init_script.sql o python -m scripts.cargar_db_demo."
        )

    columnas = {c["name"] for c in insp.get_columns("business_entities")}

    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in columnas]

    if faltan:

        raise RuntimeError(
            "El esquema de business_entities está incompleto. Faltan: "
            + ", ".join(faltan)
            + ". Aplique las migraciones 005 y 006, o python -m scripts.cargar_db_demo."
        )

    if not insp.has_table("business_reputation_metrics"):

        raise RuntimeError(
            "Falta business_reputation_metrics. Corra db/init_script.sql o python -m scripts.cargar_db_demo."
        )

def sembrar(reset: bool, purge_all: bool = False) -> None:

    engine = obtener_motor()

    _verificar_esquema(engine)

    session = sessionmaker(bind=engine, expire_on_commit=False)()

    try:

        if purge_all:

            borrados = session.execute(text("DELETE FROM business_entities")).rowcount

            session.commit()

            print(f"Negocios eliminados: {borrados}.")

        refs = [n["external_ref"] for n in NEGOCIOS]

        if reset and (not purge_all):

            for negocio in session.scalars(
                select(EntidadNegocio).where(EntidadNegocio.external_ref.in_(refs))
            ):

                session.delete(negocio)

            session.commit()

        existentes = {
            row.external_ref: row
            for row in session.scalars(
                select(EntidadNegocio).where(EntidadNegocio.external_ref.in_(refs))
            )
        }

        creados = 0

        actualizados = 0

        for n in NEGOCIOS:

            actual = existentes.get(n["external_ref"])

            if actual is None:

                negocio = EntidadNegocio(external_ref=n["external_ref"])

                _aplicar_negocio(negocio, n)

                session.add(negocio)

                session.flush()

                _aplicar_metricas(negocio, n)

                creados += 1

            else:

                _aplicar_negocio(actual, n)

                _aplicar_metricas(actual, n)

                actualizados += 1

        session.commit()

        total = session.scalar(
            text(
                "SELECT count(*) FROM business_entities WHERE external_ref LIKE 'seed:%'"
            )
        )

        print(
            f"Negocios demo creados: {creados}. Actualizados: {actualizados}. Total seed: {total}. Catálogo: {len(NEGOCIOS)}."
        )

    finally:

        session.close()

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Siembra negocios B2B del marketplace."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra los negocios seed:* y los recrea desde cero.",
    )

    parser.add_argument(
        "--purge-all",
        action="store_true",
        help="Borra TODOS los negocios de la base y siembra el catálogo B2B.",
    )

    args = parser.parse_args()

    try:

        sembrar(reset=args.reset, purge_all=args.purge_all)

    except RuntimeError as e:

        print(e, file=sys.stderr)

        raise SystemExit(1) from e

if __name__ == "__main__":

    main()
