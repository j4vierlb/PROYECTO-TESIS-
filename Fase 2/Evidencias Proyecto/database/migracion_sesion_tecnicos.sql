-- Migración para bases de datos que ya existen (schema.sql solo se aplica
-- al crear la base desde cero): agrega session_version a operadores, igual
-- que en usuarios. Cuando el administrador cambia la clave de un técnico
-- desde el panel, este número sube y los tokens ya entregados a la app dejan
-- de servir. Los tokens actuales siguen válidos porque empiezan en 0.
-- Es segura de ejecutar más de una vez.
--
-- Uso:
--   docker compose exec -T db psql -U killbichos -d killbichos < migracion_sesion_tecnicos.sql

ALTER TABLE operadores
    ADD COLUMN IF NOT EXISTS session_version INTEGER NOT NULL DEFAULT 0;
