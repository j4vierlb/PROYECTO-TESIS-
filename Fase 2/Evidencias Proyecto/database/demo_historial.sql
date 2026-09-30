-- Visitas pasadas ya completadas, con su croquis y sus trampas, para que la
-- pantalla "Historial" de la app tenga datos de ejemplo.
--
-- Se puede correr varias veces sin duplicar nada: si ya existen, solo
-- recalcula las fechas (5 y 12 días antes de hoy).
--
-- En una base existente:
--   docker exec -i killbichos_db psql -U killbichos -d killbichos < demo_historial.sql
-- En una base nueva se carga sola (ver docker-compose.yml).

INSERT INTO visitas (id, empresa_id, cliente_id, operador_id, fecha_hora, estado, origen_agendamiento, notas)
VALUES
    (
        '99999999-0000-0000-0000-000000000001',
        '11111111-1111-1111-1111-111111111111',
        '55555555-5555-5555-5555-555555555555',
        '33333333-3333-3333-3333-333333333333',
        (date_trunc('day', now() AT TIME ZONE 'America/Santiago') - interval '5 days' + interval '14 hours') AT TIME ZONE 'America/Santiago',
        'completada',
        'whatsapp_ia',
        'Instalación inicial en bodega. Se dejaron 3 dispositivos en el perímetro.'
    ),
    (
        '99999999-0000-0000-0000-000000000002',
        '11111111-1111-1111-1111-111111111111',
        '44444444-4444-4444-4444-444444444444',
        '33333333-3333-3333-3333-333333333333',
        (date_trunc('day', now() AT TIME ZONE 'America/Santiago') - interval '12 days' + interval '15 hours') AT TIME ZONE 'America/Santiago',
        'completada',
        'manual',
        'Revisión mensual. Sin actividad de roedores; se retiró una trampa dañada.'
    )
ON CONFLICT (id) DO UPDATE
SET fecha_hora = EXCLUDED.fecha_hora,
    estado = EXCLUDED.estado,
    notas = EXCLUDED.notas;

INSERT INTO croquis (id, cliente_id, visita_id, operador_id, version, sugerido_por_ia, validado_por_operador)
VALUES
    ('99999999-0000-0000-0000-0000000000c1', '55555555-5555-5555-5555-555555555555',
     '99999999-0000-0000-0000-000000000001', '33333333-3333-3333-3333-333333333333', 1, TRUE, TRUE),
    ('99999999-0000-0000-0000-0000000000c2', '44444444-4444-4444-4444-444444444444',
     '99999999-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333', 1, TRUE, TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO dispositivos_trampa (id, croquis_id, codigo, tipo, ubicacion, sugerido_por_ia, confirmado, estado)
VALUES
    ('99999999-0000-0000-0000-0000000000d1', '99999999-0000-0000-0000-0000000000c1', 'B-01', 'cebadero',
     ST_SetSRID(ST_MakePoint(-70.60195, -33.49045), 4326)::geography, TRUE, TRUE, 'activo'),
    ('99999999-0000-0000-0000-0000000000d2', '99999999-0000-0000-0000-0000000000c1', 'B-02', 'cebadero',
     ST_SetSRID(ST_MakePoint(-70.60210, -33.49055), 4326)::geography, TRUE, TRUE, 'activo'),
    ('99999999-0000-0000-0000-0000000000d3', '99999999-0000-0000-0000-0000000000c1', 'B-03', 'trampa_luz',
     ST_SetSRID(ST_MakePoint(-70.60200, -33.49062), 4326)::geography, FALSE, TRUE, 'activo'),
    ('99999999-0000-0000-0000-0000000000d4', '99999999-0000-0000-0000-0000000000c2', 'T-01', 'cebadero',
     ST_SetSRID(ST_MakePoint(-70.59885, -33.48685), 4326)::geography, TRUE, TRUE, 'activo'),
    ('99999999-0000-0000-0000-0000000000d5', '99999999-0000-0000-0000-0000000000c2', 'T-02', 'trampa_pegamento',
     ST_SetSRID(ST_MakePoint(-70.59892, -33.48698), 4326)::geography, TRUE, TRUE, 'retirado')
ON CONFLICT (id) DO NOTHING;
