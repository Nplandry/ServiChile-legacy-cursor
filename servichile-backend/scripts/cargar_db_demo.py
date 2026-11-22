from __future__ import annotations

import argparse

import subprocess

import sys

from pathlib import Path

from sqlalchemy import inspect, text

from app.infraestructura.persistencia.modelos import obtener_motor

from scripts.sembrar_negocios import sembrar

ROOT = Path(__file__).resolve().parents[1]

MIGRACIONES = [
    ROOT / "db" / "migrations" / "003_negocios.sql",
    ROOT / "db" / "migrations" / "004_pasaporte.sql",
    ROOT / "db" / "migrations" / "005_marketplace.sql",
    ROOT / "db" / "migrations" / "006_marketplace_media.sql",
    ROOT / "db" / "migrations" / "007_biometria.sql",
    ROOT / "db" / "migrations" / "008_xp.sql",
    ROOT / "db" / "migrations" / "009_tipo_cuenta.sql",
    ROOT / "db" / "migrations" / "010_categorias_b2b.sql",
    ROOT / "db" / "migrations" / "011_drop_pasaporte_arriendo.sql",
    ROOT / "db" / "migrations" / "012_categoria_logistica.sql",
    ROOT / "db" / "migrations" / "013_ciber_observables.sql",
    ROOT / "db" / "migrations" / "014_ciber_observables_extra.sql",
    ROOT / "db" / "migrations" / "015_drop_consultas_rag.sql",
    ROOT / "db" / "migrations" / "016_drop_pgvector.sql",
    ROOT / "db" / "migrations" / "017_tipos_cuenta_proveedor.sql",
    ROOT / "db" / "migrations" / "018_antecedentes.sql",
    ROOT / "db" / "migrations" / "019_score_cookies.sql",
    ROOT / "db" / "migrations" / "020_score_mercado_publico.sql",
    ROOT / "db" / "migrations" / "021_rut_empresa.sql",
    ROOT / "db" / "migrations" / "022_score_sii.sql",
    ROOT / "db" / "migrations" / "023_cmf_indice.sql",
    ROOT / "db" / "migrations" / "024_score_incidentes.sql",
    ROOT / "db" / "migrations" / "025_incidentes_razones.sql",
    ROOT / "db" / "migrations" / "026_google_place_nombre.sql",
    ROOT / "db" / "migrations" / "027_docs_legales.sql",
    ROOT / "db" / "migrations" / "028_datalux_domicilio_huella.sql",
    ROOT / "db" / "migrations" / "029_score_persona_juridica.sql",
    ROOT / "db" / "migrations" / "030_indices_listado.sql",
    ROOT / "db" / "migrations" / "031_biometria_archivo.sql",
    ROOT / "db" / "migrations" / "032_cedula_archivo.sql",
    ROOT / "db" / "migrations" / "033_aval.sql",
    ROOT / "db" / "migrations" / "034_docs_empresa.sql",
    ROOT / "db" / "migrations" / "035_pades_antecedentes.sql",
    ROOT / "db" / "migrations" / "036_pades_trust_hashes.sql",
    ROOT / "db" / "migrations" / "037_observables_ciber_json.sql",
    ROOT / "db" / "migrations" / "038_final_score_permite_cero.sql",
    ROOT / "db" / "migrations" / "039_drop_is_verified_profile.sql",
    ROOT / "db" / "migrations" / "040_limpia_legacy_metricas_perfil.sql",
    ROOT / "db" / "migrations" / "041_hardening_esquema.sql",
    ROOT / "db" / "migrations" / "042_rename_ciber_a_rater.sql",
    ROOT / "db" / "migrations" / "043_trabajos_concretados.sql",
    ROOT / "db" / "migrations" / "044_oferta_negocio.sql",
    ROOT / "db" / "migrations" / "045_correo_oauth.sql",
    ROOT / "db" / "migrations" / "046_compras_informe.sql",
    ROOT / "db" / "migrations" / "047_compras_informe_fks.sql",
    ROOT / "db" / "migrations" / "048_compras_informe_fk_business.sql",
    ROOT / "db" / "migrations" / "049_compras_informe_unica_autorizada.sql",
    ROOT / "db" / "migrations" / "050_compras_publicacion.sql",
    ROOT / "db" / "migrations" / "051_compras_publicacion_fks.sql",
]

def _psql_url(database_url: str) -> str:

    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)

def _correr_sql(archivo: Path, database_url: str) -> None:

    url = _psql_url(database_url)

    cmd = ["psql", url, "-v", "ON_ERROR_STOP=1", "-f", str(archivo)]

    print("→", " ".join(cmd))

    subprocess.run(cmd, check=True)

def _schema_listo(engine) -> bool:

    insp = inspect(engine)

    if not insp.has_table("business_entities"):

        return False

    cols = {c["name"] for c in insp.get_columns("business_entities")}

    return {
        "direccion",
        "descripcion",
        "requiere_nivel",
        "imagen_url",
        "logo_url",
    }.issubset(cols)

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Prepara schema demo y siembra negocios."
    )

    parser.add_argument(
        "--reset-seed",
        action="store_true",
        help="Borra y recrea solo los negocios seed:*.",
    )

    parser.add_argument(
        "--solo-seed",
        action="store_true",
        help="No intenta migraciones; solo siembra si el schema ya está listo.",
    )

    args = parser.parse_args()

    engine = obtener_motor()

    database_url = str(engine.url)

    def _tiene_biometria() -> bool:

        insp = inspect(engine)

        if not insp.has_table("usuarios"):

            return False

        cols = {c["name"] for c in insp.get_columns("usuarios")}

        return "biometria_verificada" in cols

    def _tiene_xp() -> bool:

        insp = inspect(engine)

        if not insp.has_table("usuarios"):

            return False

        cols = {c["name"] for c in insp.get_columns("usuarios")}

        return "xp" in cols and insp.has_table("usuario_xp_eventos")

    def _tiene_tipo_cuenta() -> bool:

        insp = inspect(engine)

        if not insp.has_table("perfiles"):

            return False

        cols = {c["name"] for c in insp.get_columns("perfiles")}

        return "tipo_cuenta" in cols

    def _tiene_metricas_rater() -> bool:

        insp = inspect(engine)

        if not insp.has_table("business_reputation_metrics"):

            return False

        cols = {c["name"] for c in insp.get_columns("business_reputation_metrics")}

        return {"observables", "final_score", "rater_escaneado_en"}.issubset(cols)

    necesita_migrar = not args.solo_seed and (
        not _schema_listo(engine)
        or not _tiene_biometria()
        or (not _tiene_xp())
        or (not _tiene_tipo_cuenta())
        or (not _tiene_metricas_rater())
    )

    if necesita_migrar:

        print("Schema incompleto. Aplicando migraciones pendientes...")

        for migracion in MIGRACIONES:

            if not migracion.exists():

                raise SystemExit(f"No existe {migracion}")

            if (
                _schema_listo(engine)
                and _tiene_biometria()
                and _tiene_xp()
                and _tiene_tipo_cuenta()
                and (not _tiene_metricas_rater())
                and (
                    migracion.name
                    not in (
                        "037_observables_ciber_json.sql",
                        "040_limpia_legacy_metricas_perfil.sql",
                        "042_rename_ciber_a_rater.sql",
                    )
                )
            ):

                continue

            try:

                _correr_sql(migracion, database_url)

            except FileNotFoundError:

                raise SystemExit("No se encontró el comando psql en el PATH.") from None

            except subprocess.CalledProcessError as e:

                raise SystemExit(
                    f"Falló {migracion.name}. Si la tabla es de otro dueño, corra el psql como el dueño de la tabla (p. ej. `psql -d NOMBRE_DB -f ...`) o transfiera ownership."
                ) from e

    if not _schema_listo(engine):

        raise SystemExit(
            "El schema sigue incompleto. Cargue db/init_script.sql en una base nueva o aplique las migraciones manualmente."
        )

    if not _tiene_biometria():

        raise SystemExit(
            "Falta biometria_verificada en usuarios. Aplique db/migrations/007_biometria.sql con el usuario dueño de la base."
        )

    if not _tiene_xp():

        raise SystemExit(
            "Falta xp / usuario_xp_eventos. Aplique db/migrations/008_xp.sql con el usuario dueño de la base."
        )

    if not _tiene_tipo_cuenta():

        raise SystemExit(
            "Falta tipo_cuenta en perfiles. Aplique db/migrations/009_tipo_cuenta.sql con el usuario dueño de la base."
        )

    if not _tiene_metricas_rater():

        raise SystemExit(
            "Faltan columnas del evaluador en business_reputation_metrics "
            "(observables, final_score, rater_escaneado_en). "
            "Aplique migraciones 037, 040 y 042 (o db/init_script.sql en base nueva)."
        )

    with engine.connect() as conn:

        usuarios = conn.execute(text("SELECT count(*) FROM usuarios")).scalar()

        print(f"DB lista. Usuarios existentes: {usuarios}.")

    sembrar(reset=args.reset_seed)

if __name__ == "__main__":

    try:

        main()

    except RuntimeError as e:

        print(e, file=sys.stderr)

        raise SystemExit(1) from e

    except subprocess.CalledProcessError:

        raise SystemExit(1) from None
