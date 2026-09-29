-- Migración para bases de datos que ya existen (schema.sql solo se aplica
-- al crear la base desde cero): agrega el MessageSid de Twilio a
-- mensajes_whatsapp, para no procesar dos veces el mismo mensaje cuando
-- Twilio reintenta el webhook. Es segura de ejecutar más de una vez.
--
-- Uso:
--   docker exec -i killbichos_db psql -U killbichos -d killbichos < migracion_message_sid.sql

ALTER TABLE mensajes_whatsapp
    ADD COLUMN IF NOT EXISTS message_sid VARCHAR(100) UNIQUE;
