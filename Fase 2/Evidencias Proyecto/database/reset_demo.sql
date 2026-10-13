-- Restablece los datos de prueba a su estado inicial, sin borrar la base.
-- Sirve para repetir una demo: la visita vuelve a quedar agendada para HOY
-- a las 10:00 (hora de Chile) y las trampas vuelven a estar sin confirmar, en su lugar.
--
-- Uso:
--   docker exec -i killbichos_db psql -U killbichos -d killbichos < reset_demo.sql

UPDATE visitas
SET fecha_hora = (date_trunc('day', now() AT TIME ZONE 'America/Santiago') + interval '10 hours') AT TIME ZONE 'America/Santiago',
    estado = 'agendada',
    notas = NULL
WHERE id = '77777777-7777-7777-7777-777777777777';

UPDATE dispositivos_trampa
SET confirmado = FALSE,
    estado = 'activo',
    ubicacion = CASE codigo
        WHEN 'T-01' THEN ST_SetSRID(ST_MakePoint(-70.59885, -33.48685), 4326)::geography
        WHEN 'T-02' THEN ST_SetSRID(ST_MakePoint(-70.59895, -33.48695), 4326)::geography
        WHEN 'T-03' THEN ST_SetSRID(ST_MakePoint(-70.59880, -33.48700), 4326)::geography
        ELSE ubicacion
    END
WHERE croquis_id = '88888888-8888-8888-8888-888888888888';
