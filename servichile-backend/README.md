# ServiChile API

Backend de ServiChile: autenticación, Reporte de Confianza, marketplace B2B e Índice de Transparencia.

Stack: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL.

## Estructura

```
servichile-backend/
├── app/
│   ├── principal.py             # App FastAPI
│   ├── configuracion.py         # Variables entorno
│   ├── tiempo.py                # Reloj UTC
│   ├── dominio/                 # Núcleo dominio
│   │   ├── entidades.py         # Entidades negocio
│   │   ├── errores.py           # Errores dominio
│   │   ├── puertos.py           # Contratos puertos
│   │   ├── rut.py               # Validación RUT
│   │   ├── reporte_estado.py    # Estado reporte
│   │   ├── ficha_negocio.py     # Ficha empresa
│   │   └── transparencia/       # Índice transparencia
│   ├── servicios/               # Casos uso
│   │   ├── autenticacion.py     # Registro login
│   │   └── reporte_identidad.py, reporte.py, trabajo.py, negocio.py
│   ├── infraestructura/         # Adaptadores externos
│   │   ├── persistencia/        # ORM SQL
│   │   ├── evaluador/           # Fuentes índice
│   │   ├── seguridad/           # Hash JWT
│   │   └── limite_solicitudes.py # Rate limit
│   ├── ensamblado/              # Factory background
│   └── api/                     # Capa REST
│       ├── esquemas/            # Contratos Pydantic
│       ├── mapeos.py            # Entidad a respuesta
│       ├── dependencias.py      # Inyección dependencias
│       ├── autorizacion.py      # Permisos API
│       └── v1/                  # Routers v1
├── db/init_script.sql           # Esquema inicial
└── tests/                       # Pruebas pytest
```

Las reglas de capas se verifican con import-linter lint-imports, ver .importlinter: el dominio no depende de frameworks, los servicios no importan infraestructura ni API, y los routers no acceden a la base. app.api.dependencias y app.ensamblado ensamblan repositorios, evaluador y loops de background.

## Endpoints

| Método | Ruta | Sesión | Descripción | Archivo | Estado |
|---|---|---|---|---|---|
| GET | /salud | No | Healthcheck | app.principal | Implementado y probado |
| POST | /v1/auth/registro | No | Registra usuario | app.api.v1.autenticacion | Implementado y probado |
| POST | /v1/auth/login | No | Login JWT | app.api.v1.autenticacion | Implementado y probado |
| GET | /v1/auth/yo | Sí | Datos del usuario autenticado | app.api.v1.autenticacion | Implementado y probado |
| GET | /v1/perfil | Sí | Estado del Reporte de Confianza | app.api.v1.perfil | Implementado y probado |
| PATCH | /v1/perfil | Sí | Actualiza edad, teléfono y verifica el RUT | app.api.v1.perfil | Implementado y probado |
| POST | /v1/perfil/biometria | Sí | Verificación biométrica | app.api.v1.perfil | Implementado y probado |
| GET | /v1/trabajos | Sí | Trabajos del usuario con su código QR | app.api.v1.trabajos | Implementado y probado |
| POST | /v1/trabajos | Sí | Abre un trabajo con un proveedor | app.api.v1.trabajos | Implementado y probado |
| DELETE | /v1/trabajos/{id} | Sí | Cancela un trabajo propio abierto | app.api.v1.trabajos | Implementado y probado |
| DELETE | /v1/auth/yo | Sí | Elimina la cuenta con confirmación por contraseña | app.api.v1.autenticacion | Implementado y probado |
| GET | /v1/businesses | No | Marketplace público | app.api.v1.negocios | Implementado y probado |
| POST | /v1/businesses | Sí, proveedor | Crea empresa | app.api.v1.negocios | Implementado y probado |
| GET | /v1/businesses/mias | Sí | Empresas del titular | app.api.v1.negocios | Implementado y probado |
| POST | /v1/businesses/{id}/rater-refresh | Sí, titular | Re-evalúa evaluador e índice | app.api.v1.negocios | Implementado y probado |
| POST | /v1/businesses/{id}/trabajos/concretar | Sí, titular | Marca trabajo concretado con QR | app.api.v1.trabajos | Implementado y probado |
| POST | /v1/businesses/{id}/trabajos/{id}/no-concretado | Sí, titular | Marca no concretado | app.api.v1.trabajos | Implementado y probado |
| GET | /v1/businesses/{id}/reputation | No | Índice de Transparencia | app.api.v1.negocios | Implementado y probado |
| DELETE | /v1/businesses/{id} | Sí, creador | Elimina la empresa | app.api.v1.negocios | Implementado y probado |

Los endpoints con Sí en Sesión requieren la cabecera Authorization Bearer access_token.

## Levantar en local

Requisitos: Python 3.12 y PostgreSQL. Ejemplo con Docker:

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

Luego:

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"

psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql

uvicorn app.principal:app --reload
```

Pegue el valor generado en JWT_SECRET del .env.

Abra la documentación OpenAPI en el puerto 8000 para probar los endpoints, o importe la colección Postman en tests.

## Pruebas

```bash
pytest
```

Las pruebas unitarias usan SQLite en memoria. No necesitan PostgreSQL.

## Configuración

Precios viven en el dominio

| Variable | Obligatoria | Notas |
|----------|-------------|--------|
| APP_ENV | sí | local, test pytest, production |
| DATABASE_URL | sí | Postgres |
| JWT_SECRET | sí | al menos 32 chars |
| CORS_ORIGINS | sí en prod | coma-separados; en prod no puede ser solo localhost |
| CHILECOMPRA_TICKET | no | vacío simula ChileCompra; con ticket API real |
| GOOGLE_PLACES_API_KEY | no | vacío simula Places |
| REDIS_URL | sí salvo test | Redis local en puerto 6379 |
| TRUST_PROXY | no | solo detrás de proxy confiable |

Verificador RUT: no va en .env. Se deriva según entorno y ticket ChileCompra.

# ServiChile PWA

Aplicación web progresiva de **catálogo B2B** e índice de transparencia de proveedores.

Archivo [readme.md](http://readme.md) con informacion basica del compontente frontend pero hay un documento adicional oficial completo en el repositorio.

| Ruta | Archivo | Función |
| --- | --- | --- |
| / | index.html | Acceso y app completa |
| /onboarding/ | index.html | Alta proveedor, contratista, persona |

Vistas internas:

- **Explorar**: proveedores B2B con índice de transparencia.
- **Reportes**: informe imprimible, QR y validador.
- **Nivel de verificacion**
- **Perfil**: datos de cuenta y estado de verificación.

## Estructura

| Ruta | Contenido |
| --- | --- |
| index.html | Estructura de vistas |
| onboarding/index.html | Bienvenida |
| css/styles.css | Estilos |
| js/app.js | Vistas, menú y perfil |
| js/core/auth.js | Sesión API |
| js/core/security.js | RUT en cliente |
| js/compliance.js | Cookies e incidentes locales |
| js/modules/market.js | Explorar proveedores |
| js/modules/reporte-qr.js | Emisión y validación del QR del reporte |
| js/modules/subir-confianza.js | Verificación |
| js/modules/reporte-persona.js | Informe persona |
| js/modules/reporte-empresa.js | Informe empresa |
| js/modules/progreso-cuenta.js | Estrategia proveedor, contratista, persona |
| js/onboarding.js | Alta de cuenta |
| sw.js | Service Worker |
| manifest.json | PWA |

# Cómo levantar

## Backend

```bash
cd servichile-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegue el token en JWT_SECRET del .env.

### Postgres

```bash
docker run -d --name servichile-db -p 5432:5432 \
  -e POSTGRES_USER=servichile -e POSTGRES_PASSWORD=servichile -e POSTGRES_DB=servichile \
  postgres:16
```

### Redis

```bash
docker run -d --name servichile-redis -p 6379:6379 redis:7-alpine
```

En .env: REDIS_URL=redis://localhost:6379/0

### Mailhog

```bash
docker run -d --name servichile-mailhog -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

En .env: SMTP_HOST=127.0.0.1, SMTP_PORT=1025, SMTP_DESDE=noreply@servichile.local, SMTP_STARTTLS=false

### Base nueva

```bash
psql "postgresql://servichile:servichile@localhost:5432/servichile" -v ON_ERROR_STOP=1 -f db/init_script.sql
python -m scripts.cargar_db_demo
uvicorn app.principal:app --reload
```

### Base ya existente

```bash
python -m scripts.cargar_db_demo
```

Refrescar seed:

```bash
python -m scripts.cargar_db_demo --reset-seed
```

### Arranque diario

```bash
cd ~/Desktop/pwa2/servichile-backend
source .venv/bin/activate
uvicorn app.principal:app --reload --port 8000
```

### Migraciones de compras (VPS / production)

```bash
cd ~/servichile-backend
source .venv/bin/activate
python -m scripts.aplicar_migraciones_compras
```

## Frontend

```bash
cd servichile-frontend
python3 serve.py 5500
```

```
API:       http://localhost:8000/docs
Frontend:  http://localhost:5500/index.html
Salud:     http://localhost:8000/salud
```

## Tests

```bash
cd servichile-backend
source .venv/bin/activate
pytest
lint-imports
```
