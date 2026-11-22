

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MIGRACIONES = [
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

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aplica migraciones 046–051 (compras informe/publicación) en Postgres."
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Override DATABASE_URL (postgresql+psycopg://…).",
    )
    parser.add_argument(
        "--desde",
        choices=("046", "047", "048", "049", "050", "051"),
        default="046",
        help="Primera migración a aplicar (default 046).",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    if args.database_url.strip():
        database_url = args.database_url.strip()
    else:
        from app.configuracion import obtener_configuracion

        database_url = obtener_configuracion().database_url

    if "sqlite" in database_url.lower():
        raise SystemExit(
            "Este script es solo para Postgres (VPS/production). "
            "DATABASE_URL apunta a SQLite."
        )

    start = f"{args.desde}_"
    aplicar = False
    for migracion in MIGRACIONES:
        if migracion.name.startswith(start):
            aplicar = True
        if not aplicar:
            continue
        if not migracion.exists():
            raise SystemExit(f"No existe {migracion}")
        try:
            _correr_sql(migracion, database_url)
        except FileNotFoundError:
            raise SystemExit("No se encontró psql en el PATH.") from None
        except subprocess.CalledProcessError as e:
            raise SystemExit(
                f"Falló {migracion.name} (exit {e.returncode}). "
                "Si es 047/048/051 por privilegios: corra como owner de las tablas "
                "referenciadas o GRANT REFERENCES. Ver COMO_LEVANTAR.md."
            ) from e
        print(f"OK {migracion.name}")

    print(
        "Listo. Reinicie uvicorn. En production deben pasar "
        "verificar_fks_compras_informe y verificar_compras_publicacion "
        "(FKs 047–048/051 + índices 049/050). Si 051 solo hizo NOTICE, "
        "verifique: SELECT conname FROM pg_constraint WHERE conname LIKE "
        "'compras_publicacion%';"
    )

if __name__ == "__main__":
    main()
