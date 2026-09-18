-- =====================================================================
-- Kill Bichos - Datos de prueba (seed)
-- =====================================================================

-- Empresa
INSERT INTO empresas (id, nombre, comuna, telefono)
VALUES ('11111111-1111-1111-1111-111111111111', 'Kill Bichos', 'Macul', '+56912345678');

-- Usuario admin del panel web
-- Clave de prueba para ambas cuentas: "demo1234" (hash real generado con
-- passlib/bcrypt, ver backend/app/security.py). Solo para desarrollo.
INSERT INTO usuarios (id, empresa_id, nombre, email, password_hash, rol)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Admin Kill Bichos',
    'admin@killbichos.cl',
    '$2b$12$PmmajHoq0kFx94SOQ.HZUeZrYjCxyt4UA2XbbtbZMBM4g3sd4bNha',
    'admin'
);

-- Operador de terreno (app móvil)
INSERT INTO operadores (id, empresa_id, nombre, telefono, email, password_hash)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    'Juan Técnico',
    '+56987654321',
    'tecnico1@killbichos.cl',
    '$2b$12$PmmajHoq0kFx94SOQ.HZUeZrYjCxyt4UA2XbbtbZMBM4g3sd4bNha'
);

-- Clientes (coordenadas de referencia en Macul, Santiago)
INSERT INTO clientes (id, empresa_id, nombre, telefono_whatsapp, direccion, ubicacion)
VALUES
    (
        '44444444-4444-4444-4444-444444444444',
        '11111111-1111-1111-1111-111111111111',
        'Restaurante Don José',
        '+56911111111',
        'Av. Macul 1234, Macul',
        ST_SetSRID(ST_MakePoint(-70.5989, -33.4869), 4326)::geography
    ),
    (
        '55555555-5555-5555-5555-555555555555',
        '11111111-1111-1111-1111-111111111111',
        'Bodega Central Ltda.',
        '+56922222222',
        'Av. Departamental 567, Macul',
        ST_SetSRID(ST_MakePoint(-70.6020, -33.4905), 4326)::geography
    );

-- Conversación de WhatsApp de ejemplo
INSERT INTO conversaciones_whatsapp (id, cliente_id, estado)
VALUES ('66666666-6666-6666-6666-666666666666', '44444444-4444-4444-4444-444444444444', 'cerrada');

INSERT INTO mensajes_whatsapp (conversacion_id, emisor, contenido, intencion_detectada)
VALUES
    ('66666666-6666-6666-6666-666666666666', 'cliente', 'Hola, necesito agendar una visita de control de plagas', 'agendar_visita'),
    ('66666666-6666-6666-6666-666666666666', 'agente_ia', 'Claro, tengo disponibilidad el jueves a las 10:00 o el viernes a las 15:00. ¿Cuál prefieres?', NULL),
    ('66666666-6666-6666-6666-666666666666', 'cliente', 'El jueves a las 10 está bien', 'confirmar_horario');

-- Visita agendada para "hoy" a las 10:00 UTC, para que aparezca de entrada
-- en GET /operadores/me/visitas-hoy al levantar el proyecto desde cero.
INSERT INTO visitas (id, empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento)
VALUES (
    '77777777-7777-7777-7777-777777777777',
    '11111111-1111-1111-1111-111111111111',
    '44444444-4444-4444-4444-444444444444',
    '33333333-3333-3333-3333-333333333333',
    date_trunc('day', now() AT TIME ZONE 'UTC') + interval '10 hours',
    'agendada',
    'whatsapp_ia'
);

-- Croquis asociado a la visita
INSERT INTO croquis (id, cliente_id, visita_id, operador_id, version, sugerido_por_ia, validado_por_operador)
VALUES (
    '88888888-8888-8888-8888-888888888888',
    '44444444-4444-4444-4444-444444444444',
    '77777777-7777-7777-7777-777777777777',
    '33333333-3333-3333-3333-333333333333',
    1,
    TRUE,
    FALSE
);

-- Dispositivos/trampas sugeridos por IA sobre el croquis
INSERT INTO dispositivos_trampa (croquis_id, codigo, tipo, ubicacion, sugerido_por_ia, confirmado)
VALUES
    ('88888888-8888-8888-8888-888888888888', 'T-01', 'cebadero', ST_SetSRID(ST_MakePoint(-70.59885, -33.48685), 4326)::geography, TRUE, FALSE),
    ('88888888-8888-8888-8888-888888888888', 'T-02', 'cebadero', ST_SetSRID(ST_MakePoint(-70.59895, -33.48695), 4326)::geography, TRUE, FALSE),
    ('88888888-8888-8888-8888-888888888888', 'T-03', 'trampa_pegamento', ST_SetSRID(ST_MakePoint(-70.59880, -33.48700), 4326)::geography, TRUE, FALSE);
