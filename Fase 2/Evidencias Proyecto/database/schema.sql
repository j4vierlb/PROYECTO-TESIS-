-- =====================================================================
-- Kill Bichos - Esquema de base de datos (PostgreSQL + PostGIS)
-- Proyecto APT: automatización de agendamiento y croquis asistido por IA
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------
-- Empresa (pensado con soporte multi-tenant a futuro, aunque hoy
-- el único cliente real del proyecto es Kill Bichos, comuna de Macul)
-- ---------------------------------------------------------------------
CREATE TABLE empresas (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre      VARCHAR(150) NOT NULL,
    comuna      VARCHAR(100),
    telefono    VARCHAR(30),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Usuarios del panel web (administración de la empresa)
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id     UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre         VARCHAR(150) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    rol            VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'coordinador')),
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Operadores de terreno (usuarios de la app móvil)
-- ---------------------------------------------------------------------
CREATE TABLE operadores (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id     UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre         VARCHAR(150) NOT NULL,
    telefono       VARCHAR(30),
    email          VARCHAR(150) UNIQUE,
    password_hash  TEXT NOT NULL,
    activo         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Clientes finales de la empresa de plagas
-- ---------------------------------------------------------------------
CREATE TABLE clientes (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id         UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre             VARCHAR(150) NOT NULL,
    telefono_whatsapp  VARCHAR(30) NOT NULL UNIQUE,
    direccion          TEXT,
    ubicacion          GEOGRAPHY(Point, 4326), -- coordenadas del predio
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Conversaciones de WhatsApp por cliente (hilo del agente de IA)
-- ---------------------------------------------------------------------
CREATE TABLE conversaciones_whatsapp (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id  UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    estado      VARCHAR(20) NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa', 'cerrada')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE mensajes_whatsapp (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversacion_id       UUID NOT NULL REFERENCES conversaciones_whatsapp(id) ON DELETE CASCADE,
    emisor                VARCHAR(10) NOT NULL CHECK (emisor IN ('cliente', 'agente_ia', 'sistema')),
    contenido             TEXT NOT NULL,
    intencion_detectada   VARCHAR(50), -- ej: 'agendar_visita', 'consulta', 'reagendar'
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Visitas agendadas (por el agente de IA o manualmente)
-- ---------------------------------------------------------------------
CREATE TABLE visitas (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id            UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cliente_id            UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    operador_id           UUID REFERENCES operadores(id),
    fecha_hora            TIMESTAMPTZ NOT NULL,
    estado                VARCHAR(20) NOT NULL DEFAULT 'agendada'
                           CHECK (estado IN ('agendada', 'en_curso', 'completada', 'cancelada', 'reagendada')),
    origen_agendamiento   VARCHAR(20) NOT NULL DEFAULT 'whatsapp_ia'
                           CHECK (origen_agendamiento IN ('whatsapp_ia', 'manual')),
    notas                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Croquis: versión del plano de ubicación de trampas para un cliente,
-- generalmente ligado a una visita
-- ---------------------------------------------------------------------
CREATE TABLE croquis (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id              UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    visita_id               UUID REFERENCES visitas(id),
    operador_id             UUID REFERENCES operadores(id),
    version                 INT NOT NULL DEFAULT 1,
    imagen_satelital_url    TEXT,
    sugerido_por_ia         BOOLEAN NOT NULL DEFAULT FALSE,
    validado_por_operador   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Dispositivos (cebaderos / trampas) ubicados dentro de un croquis
-- ---------------------------------------------------------------------
CREATE TABLE dispositivos_trampa (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    croquis_id       UUID NOT NULL REFERENCES croquis(id) ON DELETE CASCADE,
    codigo           VARCHAR(30), -- etiqueta física del dispositivo, ej. "T-01"
    tipo             VARCHAR(30) CHECK (tipo IN ('cebadero', 'trampa_pegamento', 'trampa_luz', 'otro')),
    ubicacion        GEOGRAPHY(Point, 4326) NOT NULL,
    sugerido_por_ia  BOOLEAN NOT NULL DEFAULT FALSE,
    confirmado       BOOLEAN NOT NULL DEFAULT FALSE,
    estado           VARCHAR(20) NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'retirado', 'revisar')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Índices
-- ---------------------------------------------------------------------
CREATE INDEX idx_clientes_ubicacion      ON clientes USING GIST (ubicacion);
CREATE INDEX idx_dispositivos_ubicacion  ON dispositivos_trampa USING GIST (ubicacion);
CREATE INDEX idx_visitas_operador_fecha  ON visitas (operador_id, fecha_hora);
CREATE INDEX idx_visitas_cliente         ON visitas (cliente_id);
CREATE INDEX idx_mensajes_conversacion   ON mensajes_whatsapp (conversacion_id, created_at);
