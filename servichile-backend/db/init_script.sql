

BEGIN;

CREATE TABLE usuarios (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email          varchar(254) NOT NULL UNIQUE CHECK (email = lower(email)),
    nombre         varchar(120) NOT NULL,
    password_hash  text NOT NULL,
    activo         boolean NOT NULL DEFAULT true,
    rut            varchar(12) UNIQUE CHECK (rut IS NULL OR rut ~ '^[0-9]{1,8}-[0-9K]$'),
    rut_verificado boolean NOT NULL DEFAULT false,
    telefono       varchar(30),
    biometria_verificada boolean NOT NULL DEFAULT false,
    biometria_verificada_en timestamptz,
    biometria_ruta varchar(260),
    biometria_sha256 varchar(64),
    biometria_bytes integer,
    biometria_ancho integer,
    biometria_alto integer,
    biometria_content_type varchar(40),
    biometria_retener_hasta timestamptz,
    cedula_verificada boolean NOT NULL DEFAULT false,
    cedula_verificada_en timestamptz,
    cedula_ruta varchar(260),
    cedula_sha256 varchar(64),
    cedula_bytes integer,
    cedula_ancho integer,
    cedula_alto integer,
    cedula_content_type varchar(40),
    cedula_retener_hasta timestamptz,
    cedula_score integer,
    cedula_rut_ocr varchar(12),
    antecedentes_verificados boolean NOT NULL DEFAULT false,
    antecedentes_verificados_en timestamptz,
    antecedentes_anotaciones boolean,
    antecedentes_score integer,
    antecedentes_pades boolean NOT NULL DEFAULT false,
    antecedentes_entidad_emisora text,
    antecedentes_fecha_emision date,
    antecedentes_sha256 text,
    antecedentes_glosa text,
    aval_verificado boolean NOT NULL DEFAULT false,
    aval_verificado_en timestamptz,
    aval_score integer,
    aval_tipo varchar(20),
    xp             integer NOT NULL DEFAULT 0 CHECK (xp >= 0),
    creado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_usuarios_antecedentes_sha256
    ON usuarios (antecedentes_sha256)
    WHERE antecedentes_sha256 IS NOT NULL;

CREATE TABLE usuario_xp_eventos (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    evento      varchar(80) NOT NULL,
    puntos      integer NOT NULL CHECK (puntos > 0),
    creado_en   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, evento)
);

CREATE INDEX usuario_xp_eventos_usuario_idx ON usuario_xp_eventos (usuario_id, creado_en DESC);

CREATE TABLE perfiles (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    edad           smallint CHECK (edad IS NULL OR edad BETWEEN 14 AND 120),
    tipo_cuenta    varchar(20) CHECK (
        tipo_cuenta IS NULL OR tipo_cuenta IN ('persona', 'contratista', 'proveedor')
    ),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE business_entities (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre         varchar(160) NOT NULL,
    categoria      varchar(30) NOT NULL
                     CHECK (categoria IN (
                         'tecnologia', 'industria', 'construccion',
                         'servicios-profesionales', 'logistica'
                     )),
    latitud        double precision,
    longitud       double precision,
    direccion      varchar(200),
    descripcion    text,
    servicios      jsonb NOT NULL DEFAULT '[]'::jsonb,
    industrias     jsonb NOT NULL DEFAULT '[]'::jsonb,
    contrataciones jsonb NOT NULL DEFAULT '[]'::jsonb,
    monto          varchar(20)
                     CHECK (monto IS NULL OR monto IN ('bajo', 'medio', 'alto')),
    plazo          varchar(20)
                     CHECK (plazo IS NULL OR plazo IN ('menos-2h', 'en-el-dia', '24-48h')),
    referencias    jsonb NOT NULL DEFAULT '[]'::jsonb,
    imagen_url     varchar(500),
    logo_url       varchar(500),
    requiere_nivel smallint NOT NULL DEFAULT 1 CHECK (requiere_nivel IN (1, 2)),
    external_ref   varchar(200) UNIQUE,
    is_claimed     boolean NOT NULL DEFAULT false,
    reclamado_por  uuid REFERENCES usuarios(id) ON DELETE SET NULL,
    telefono       varchar(30),
    sitio_web      varchar(200),
    rut_empresa    varchar(12)
                     CHECK (rut_empresa IS NULL OR rut_empresa ~ '^[0-9]{1,8}-[0-9K]$'),
    docs_empresa   jsonb NOT NULL DEFAULT '{}'::jsonb,
    creado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX business_entities_rut_empresa_uidx
    ON business_entities (rut_empresa)
    WHERE rut_empresa IS NOT NULL;

CREATE TABLE business_reputation_metrics (
    business_id          uuid PRIMARY KEY
                         REFERENCES business_entities(id) ON DELETE CASCADE,
    google_rating_avg    double precision
                         CHECK (google_rating_avg IS NULL OR google_rating_avg BETWEEN 0 AND 5),
    google_reviews_count integer NOT NULL DEFAULT 0 CHECK (google_reviews_count >= 0),
    final_score          double precision NOT NULL DEFAULT 0.0
                         CHECK (final_score BETWEEN 0 AND 10),
    rater_escaneado_en   timestamptz,
    observables          jsonb,
    actualizado_en       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE trabajos (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id    uuid NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    estado         varchar(20) NOT NULL DEFAULT 'abierto'
                     CHECK (estado IN ('abierto', 'concretado', 'no_concretado', 'cancelado')),
    qr_token       varchar(64) NOT NULL UNIQUE,
    creado_en      timestamptz NOT NULL DEFAULT now(),
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE pades_document_hashes (
    sha256       text PRIMARY KEY,
    scope        text NOT NULL,
    tipo         text,
    usuario_id   uuid REFERENCES usuarios(id) ON DELETE SET NULL,
    business_id  uuid REFERENCES business_entities(id) ON DELETE SET NULL,
    creado_en    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_pades_hashes_business ON pades_document_hashes (business_id);

CREATE INDEX business_entities_categoria_nombre_idx ON business_entities (categoria, nombre);
CREATE INDEX business_entities_reclamado_por_idx ON business_entities (reclamado_por);
CREATE INDEX trabajos_usuario_idx ON trabajos (usuario_id, creado_en DESC);
CREATE INDEX trabajos_negocio_idx ON trabajos (business_id);

CREATE TABLE compras_informe (
    id                  uuid PRIMARY KEY,
    usuario_id          uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id         uuid NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    buy_order           varchar(26) NOT NULL UNIQUE,
    monto               integer NOT NULL,
    estado              varchar(20) NOT NULL DEFAULT 'pendiente',
    token               varchar(128),
    response_code       integer,
    authorization_code  varchar(32),
    payment_type_code   varchar(16),
    card_last4          varchar(4),
    error_codigo        varchar(64),
    error_detalle       text,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_compras_informe_token ON compras_informe (token);
CREATE INDEX idx_compras_informe_usuario ON compras_informe (usuario_id, creado_en DESC);
CREATE INDEX idx_compras_informe_autorizada
  ON compras_informe (usuario_id, business_id, estado);
CREATE UNIQUE INDEX uq_compras_informe_autorizada
  ON compras_informe (usuario_id, business_id)
  WHERE estado = 'autorizado';

CREATE TABLE compras_publicacion (
    id                  uuid PRIMARY KEY,
    usuario_id          uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id         uuid REFERENCES business_entities(id) ON DELETE SET NULL,
    buy_order           varchar(26) NOT NULL UNIQUE,
    monto               integer NOT NULL,
    estado              varchar(20) NOT NULL DEFAULT 'pendiente',
    token               varchar(128),
    response_code       integer,
    authorization_code  varchar(32),
    payment_type_code   varchar(16),
    card_last4          varchar(4),
    error_codigo        varchar(64),
    error_detalle       text,
    creado_en           timestamptz NOT NULL DEFAULT now(),
    actualizado_en      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_compras_publicacion_token ON compras_publicacion (token);
CREATE INDEX idx_compras_publicacion_usuario
  ON compras_publicacion (usuario_id, creado_en DESC);
CREATE INDEX idx_compras_publicacion_cupon
  ON compras_publicacion (usuario_id, estado)
  WHERE business_id IS NULL;

CREATE UNIQUE INDEX uq_compras_publicacion_cupon_libre
  ON compras_publicacion (usuario_id)
  WHERE estado = 'autorizado' AND business_id IS NULL;

CREATE TABLE correo_oauth (
    usuario_id     uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    email          varchar(254) NOT NULL,
    refresh_token  text NOT NULL,
    access_token   text,
    expira_en      timestamptz,
    actualizado_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE mensajes_correo (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id   uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    business_id  uuid REFERENCES business_entities(id) ON DELETE SET NULL,
    tipo         varchar(20) NOT NULL,
    destino      varchar(254) NOT NULL,
    asunto       varchar(200) NOT NULL,
    cuerpo       text NOT NULL,
    estado       varchar(20) NOT NULL,
    creado_en    timestamptz NOT NULL DEFAULT now()
);

COMMIT;
